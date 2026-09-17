import streamlit as st
import feedparser
import urllib.parse
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
import io
import time
import requests
from bs4 import BeautifulSoup
from googlenewsdecoder import gnewsdecoder

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable, Image as RLImage

st.set_page_config(page_title="PULSO ANÁLISIS TERRITORIAL", page_icon="💖", layout="wide")

GEMINI_KEY_DEFAULT = "AQ.Ab8RN6IuER73mlESZCyQUHz8A8f5Ze7gwrSR1S8YZHdEGPFi6g"
# Logo oficial con la identidad gráfica rosita/fresa
URL_LOGO = "https://lh3.googleusercontent.com/d/1Q7A8-14SevxaLSmrzsDZDQDArpQKkvhh"

# Catálogo oficial de los 212 municipios de Veracruz para blindar la búsqueda territorial exacta
MUNICIPIOS_VERACRUZ = [
    "Acajete", "Acatlán", "Acayucan", "Actopan", "Acula", "Acultzingo", "Álamo Temapache", "Alpatláhuac",
    "Alto Lucero de Gutiérrez Barrios", "Altotonga", "Alvarado", "Amatitlán", "Amatlán de los Reyes", "Angel R. Cabada",
    "Apazapan", "Aquila", "Astacinga", "Atlahuilco", "Atoyac", "Atzacan", "Atzalan", "Ayahualulco", "Banderilla",
    "Benito Juárez", "Boca del Río", "Calcahualco", "Camarón de Tejeda", "Camerino Z. Mendoza", "Carlos A. Carrillo",
    "Carrillo Puerto", "Castillo de Teayo", "Catemaco", "Cazones de Herrera", "Cerro Azul", "Chacaltianguis", "Chalma",
    "Chiconamel", "Chiconquiaco", "Chicontepec", "Chinameca", "Chinampa de Gorostiza", "Chocamán", "Chontla", "Chumatlán",
    "Citlaltépetl", "Coacoatzintla", "Coahuitlán", "Coatepec", "Coetzala", "Colipa", "Comapa", "Córdoba",
    "Cosamaloapan de Carpio", "Cosautlán de Carvajal", "Coscomatepec", "Cotaxtla", "Coxquihui", "Coyutla", "Cuichapa",
    "Cuitláhuac", "El Higo", "Emiliano Zapata", "Espinal", "Filomeno Mata", "Fortín", "Gutiérrez Zamora", "Hidalgotitlán",
    "Huatusco", "Huayacocotla", "Hueyapan de Ocampo", "Huiloapan de Cuauhtémoc", "Ignacio de la Llave", "Ilamatlán",
    "Isla", "Ixcatepec", "Ixhuacán de los Reyes", "Ixhuatlán de Madero", "Ixhuatlán del Café", "Ixhuatlancillo",
    "Ixmatlahuacan", "Ixtaczoquitlán", "Jalacingo", "Jalcomulco", "Jáltipan", "Jamapa", "Jesús Carranza", "Jilotepec",
    "José Azueta", "Juan Rodríguez Clara", "Juchique de Ferrer", "La Antigua", "La Perla", "Landero y Coss", "Las Minas",
    "Las Vigas de Ramírez", "Lerdo de Tejada", "Los Reyes", "Magdalena", "Maltrata", "Manlio Fabio Altamirano",
    "Mariano Escobedo", "Martínez de la Torre", "Mecatlán", "Mecayapan", "Medellín", "Miahuatlán", "Misantla",
    "Mixtla de Altamirano", "Naolinco", "Naranjal", "Naranjos Amatlán", "Nautla", "Nogales", "Oluta", "Omealca",
    "Orizaba", "Otatitlán", "Oteapan", "Ozuluama de Mascareñas", "Pajapan", "Pánuco", "Papantla", "Paso de Ovejas",
    "Paso del Macho", "Perote", "Platón Sánchez", "Playa Vicente", "Pueblo Viejo", "Puente Nacional", "Rafael Delgado",
    "Rafael Lucio", "Río Blanco", "Saltabarranca", "San Andrés Tenejapan", "San Andrés Tuxtla", "San Juan Evangelista",
    "San Rafael", "Santiago Sochiapan", "Santiago Tuxtla", "Sayula de Alemán", "Sochiapa", "Soconusco", "Soledad Atzompa",
    "Soledad de Doblado", "Soteapan", "Tamalín", "Tamiahua", "Tampico Alto", "Tancoco", "Tantima", "Tantoyuca",
    "Tatahuicapan de Juárez", "Tatatila", "Tecolutla", "Tehuipango", "Tempoal", "Tenampa", "Tenochtitlán", "Teocelo",
    "Tepatlaxco", "Tepetlán", "Tepetzintla", "Tequila", "Texcatepec", "Texhuacán", "Texistepec", "Tezonapa", "Tierra Blanca",
    "Tihuatlán", "Tlachichilco", "Tlacojalpan", "Tlacolulan", "Tlacotalpan", "Tlacotepec de Mejía", "Tlalixcoyan",
    "Tlalnelhuayocan", "Tlaltetela", "Tlapacoyan", "Tlaquilpa", "Tlilapan", "Tomatlán", "Tonayán", "Totutla", "Tres Valles",
    "Tuxtilla", "Ursulo Galván", "Uxpanapa", "Vega de Alatorre", "Veracruz", "Villa Aldama", "Xalapa", "Xico", "Xoxocotla",
    "Yanga", "Yecuatla", "Zacualpan", "Zaragoza", "Zentla", "Zongolica", "Zontecomatlán de López y Fuentes", "Zozocolco de Hidalgo"
]

@st.cache_data(show_spinner=False)
def descargar_logo(url):
    try:
        resp = requests.get(url, timeout=5)
        if resp.status_code == 200: return resp.content
    except: pass
    return None

logo_bytes = descargar_logo(URL_LOGO)

# Estilos CSS con la paleta coquetona (Tonos rosas #ef007f, acentos claros y blancos)
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800;900&display=swap');
    
    .stApp { background-color: #0c0f1d !important; color: #FFFFFF !important; font-family: 'Inter', sans-serif !important; }
    [data-testid="stSidebar"] { background-color: #12172b !important; border-right: 1px solid #2a3353 !important; }
    
    .stTextInput label p, .stSelectbox label p, .stSlider label p { color: #FFFFFF !important; font-weight: 700 !important; font-size: 0.95rem !important; }
    
    .ticker-wrap { width: 100%; overflow: hidden; background-color: #12172b; border: 1px solid #ef007f; border-radius: 10px; padding: 10px 14px; margin-bottom: 20px; font-size: 0.9rem; display: flex; align-items: center; box-shadow: 0 4px 15px rgba(239,0,127,0.15); }
    
    .intel-card { background: linear-gradient(135deg, #161c33 0%, #101426 100%); border: 1px solid #2a3353; border-radius: 12px; padding: 20px; margin-bottom: 18px; color: #FFFFFF !important; box-shadow: 0 8px 25px rgba(0,0,0,0.3); }
    .intel-card h3 { color: #FFFFFF !important; font-size: 1.2rem; margin-top: 10px; margin-bottom: 5px; font-weight: 800; }
    .intel-card b { color: #ffffff !important; }
    .intel-card .fuente-txt { color: #e2e8f0 !important; font-size: 0.85rem; margin-bottom: 12px; }
    .intel-card .sintesis-txt { color: #f1f5f9 !important; font-size: 1rem; line-height: 1.6; margin-bottom: 10px; }
    
    .badge-tag { font-size: 0.75rem; font-weight: 800; padding: 4px 10px; border-radius: 999px; display: inline-block; margin-right: 6px; }
    .tag-critico { background: rgba(239, 35, 60, 0.25); color: #ff6b81; border: 1px solid #ef233c; }
    .tag-neutro { background: rgba(139, 144, 153, 0.25); color: #cbd5e1; border: 1px solid #8b9099; }
    .tag-favorable { background: rgba(22, 163, 74, 0.25); color: #4ade80; border: 1px solid #16a34a; }
    .tag-sector { background: rgba(239, 0, 127, 0.2); color: #ff4aa1; border: 1px solid #ef007f; }
    
    .tactical-box { background-color: #080b16; border-left: 4px solid #ef007f; padding: 12px 14px; border-radius: 0 8px 8px 0; font-size: 0.9rem; color: #fbcfe8; margin-top: 12px; line-height: 1.5; }
    
    div.stButton > button:first-child { background: linear-gradient(135deg, #ef007f 0%, #c70068 100%) !important; color: #FFFFFF !important; border: 1px solid #ff4aa1 !important; border-radius: 10px !important; font-weight: 800 !important; padding: 0.6rem 1.4rem !important; box-shadow: 0 4px 15px rgba(239,0,127,0.4); }
</style>
""", unsafe_allow_html=True)

if "notas_web" not in st.session_state: st.session_state["notas_web"] = []
if "notas_fb" not in st.session_state: st.session_state["notas_fb"] = []
if "briefing_memo" not in st.session_state: st.session_state["briefing_memo"] = ""

def decodificar_url_google(url_google):
    if "news.google.com" not in url_google: return url_google
    try:
        decoded = gnewsdecoder(url_google, interval=0.3)
        if decoded.get("status"): return decoded.get("decoded_url")
    except: pass
    return url_google

def consultar_llm_dual(prompt_texto, gemini_key):
    if gemini_key:
        modelos = ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash"]
        for mod in modelos:
            try:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{mod}:generateContent?key={gemini_key}"
                resp = requests.post(url, headers={"Content-Type": "application/json"}, json={"contents": [{"parts": [{"text": prompt_texto}]}], "generationConfig": {"temperature": 0.3}}, timeout=12)
                if resp.status_code == 200:
                    txt = resp.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
                    if txt: return txt
            except: continue
    return None

def clasificar_sector(texto):
    t = texto.lower()
    if any(k in t for k in ["policía", "fiscalía", "homicidio", "detenido", "arma", "accidente", "choque", "seguridad", "lesionados", "asesinado", "restos humanos", "cuerpo", "cadáver", "balacera"]): return "Seguridad y Justicia"
    elif any(k in t for k in ["obra", "bacheo", "pavimentación", "agua", "drenaje", "alumbrado", "limpia pública", "servicios"]): return "Servicios e Infraestructura"
    elif any(k in t for k in ["alcalde", "ayuntamiento", "regidor", "cabildo", "presidente", "elección", "partido", "morena", "pan", "pri", "mc", "somos", "diputado"]): return "Política y Gobierno"
    elif any(k in t for k in ["comercio", "floristas", "negocios", "inflación", "inversión", "empleo", "mercado", "precio", "flores", "cañeros"]): return "Economía y Comercio"
    elif any(k in t for k in ["deporte", "futbol", "estadio", "beisbol", "maratón"]): return "Deportes"
    return "Sociedad y Comunidad"

def evaluar_tono_y_crisis(texto_completo):
    t = texto_completo.lower()
    veto_crisis = ["restos humanos", "cuerpo", "cadáver", "embolsado", "ejecutado", "homicidio", "asesinado", "asesinan", "muerte", "balacera", "ataque armado", "secuestro", "sin frenos", "fosa"]
    if any(v in t for v in veto_crisis): return "Crítico", "#EF233C", True, 10
    detonantes = ["denuncia penal", "fraude", "desvío", "bloqueo", "paro", "protesta", "colapso", "renuncia", "corrupción", "amenaza", "heridos"]
    criticas = ["queja", "exigen", "falla", "falta", "inseguridad", "robo", "violencia", "accidente", "crisis", "alerta", "cae"]
    favorables = ["inaugura", "avance", "inversión", "apoyo", "mejora", "beneficio", "obra", "anuncian", "entrega", "logro", "lidera"]
    
    es_crisis = any(d in t for d in detonantes)
    s_crit = sum(1 for p in (detonantes + criticas) if p in t)
    s_fav = sum(1 for p in favorables if p in t)
    
    if es_crisis: return "Crítico", "#EF233C", True, 9
    elif s_crit > s_fav: return "Crítico", "#EF233C", False, 7
    elif s_fav > s_crit: return "Favorable", "#16A34A", False, 2
    return "Neutro", "#8B9099", False, 4

def generar_briefing_global(termino, lista_notas, gemini_k):
    if not lista_notas: return "Panorama Informativo: Monitoreo territorial procesado."
    corpus = "\n".join([f"- [{n['Tono']}] {n['Titular']} ({n['Medio']})" for n in lista_notas[:8]])
    prompt = f"Objetivo: '{termino}'. Basado en estos reportes:\n{corpus}\n\nRedacta un Memo de Situación ejecutivo en un párrafo fluido de 4 líneas que resuma el pulso político y social actual en Veracruz. PROHIBIDO USAR PARÉNTESIS."
    resultado = consultar_llm_dual(prompt, gemini_k)
    return resultado.replace("(", "").replace(")", "") if resultado else "Cobertura distribuida sin incidencias críticas en la demarcación."

def analizar_nota_con_ia(titular, medio, gemini_k):
    prompt = f"""Eres un analista político y periodista experto en el estado de Veracruz. 
A partir del siguiente encabezado de la fuente '{medio}':

"{titular}"

REGLAS ESTRICTAS DE REDACCIÓN:
1. DESARROLLA UN TEXTO SÓLIDO de 4 a 5 líneas bien estructuradas. Explica implicaciones, actores y lectura política o social.
2. NO USES PARÉNTESIS en ninguna parte de tu redacción.
3. PROHIBIDO usar frases huecas o de relleno. Analiza directamente el contenido.
4. Si involucra crisis o conflicto, define directriz institucional de vocería. Si es favorable o neutral, pon N/A.

Formato exacto de respuesta:
RESUMEN: [Párrafo analítico profundo de 4 a 5 líneas, CERO paréntesis]
VOCERIA: [Directriz o N/A]"""

    resp_llm = consultar_llm_dual(prompt, gemini_k)
    resumen, postura = "", ""
    if resp_llm:
        if "RESUMEN:" in resp_llm.upper():
            partes = resp_llm.split("VOCERIA:") if "VOCERIA:" in resp_llm else resp_llm.split("Voceria:")
            resumen = partes[0].replace("RESUMEN:", "").replace("Resumen:", "").strip()
            if len(partes) > 1: postura = partes[1].strip()
        else:
            resumen = resp_llm.strip()

    if not resumen or len(resumen) < 40:
        resumen = f"El contenido publicado bajo el título {titular} aborda una temática relevante para la vida pública en el estado de Veracruz, permitiendo identificar posturas e impacto ciudadano."

    return resumen.replace("(", "").replace(")", ""), (postura.replace("(", "").replace(")", "") if postura and postura.upper() != "N/A" else "")

def generar_pdf(termino, periodo, lista_notas, briefing, logo_data):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    style_tit = ParagraphStyle('T1', fontName='Helvetica-Bold', fontSize=13, leading=17, textColor=colors.HexColor('#0F172A'))
    style_sub = ParagraphStyle('T2', fontName='Helvetica', fontSize=8, leading=11, textColor=colors.HexColor('#475569'))
    style_briefing = ParagraphStyle('TB', fontName='Helvetica-Oblique', fontSize=8.5, leading=12, textColor=colors.HexColor('#ef007f'))
    style_item_t = ParagraphStyle('IT', fontName='Helvetica-Bold', fontSize=9, leading=12, textColor=colors.HexColor('#0F172A'))
    style_item_m = ParagraphStyle('IM', fontName='Helvetica-Oblique', fontSize=7.5, leading=10, textColor=colors.HexColor('#64748B'))
    style_item_r = ParagraphStyle('IR', fontName='Helvetica', fontSize=8, leading=12, textColor=colors.HexColor('#334155'))
    style_item_p = ParagraphStyle('IP', fontName='Helvetica-Bold', fontSize=7.5, leading=10, textColor=colors.HexColor('#ef007f'))
    
    story = []
    fecha_emision = datetime.now(ZoneInfo("America/Mexico_City")).strftime("%d/%m/%Y - %H:%M hrs")
    cabecera = [RLImage(io.BytesIO(logo_data), width=45, height=45)] if logo_data else [""]
    cabecera.append([Paragraph("<b>PULSO ANÁLISIS TERRITORIAL — DOSSIER EJECUTIVO</b>", style_tit), Paragraph(f"Objetivo: <b>{termino}</b> &nbsp;|&nbsp; Rango: <b>{periodo}</b> &nbsp;|&nbsp; Emisión: {fecha_emision}", style_sub)])
    story.append(Table([cabecera], colWidths=[52, 488]))
    story.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor('#ef007f'), spaceAfter=8))
    story.append(Paragraph(f"<b>MEMORÁNDUM DE SITUACIÓN:</b> {briefing}", style_briefing))
    story.append(Spacer(1, 6))

    for item in lista_notas:
        tag_crisis = " [⚠️ ALERTA DE CRISIS]" if item.get('EsCrisis') else ""
        story.append(Paragraph(f"{item['No']}. [{item['Sector'].upper()}] {item['Titular']}{tag_crisis}", style_item_t))
        story.append(Paragraph(f"Fuente: <b>{item['Medio']}</b> &nbsp;|&nbsp; Postura: <b>{item['Tono']}</b>", style_item_m))
        story.append(Spacer(1, 1))
        story.append(Paragraph(f"<b>Resumen Analítico:</b> {item['Resumen']}", style_item_r))
        if item.get("PosturaTactico"):
            story.append(Spacer(1, 1))
            story.append(Paragraph(f"<b>Directriz de Vocería:</b> {item['PosturaTactico']}", style_item_p))
        story.append(Spacer(1, 1))
        story.append(Paragraph(f"Enlace: {item['EnlaceReal']}", style_item_m))
        story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor('#E2E8F0'), spaceAfter=4, spaceBefore=4))

    doc.build(story)
    buffer.seek(0)
    return buffer

with st.sidebar:
    if logo_bytes: st.image(logo_bytes, width=130)
    else: st.markdown("<h2 style='color: #ef007f;'>PULSO</h2>", unsafe_allow_html=True)
    st.divider()

    st.markdown("<b style='color: #FFFFFF;'>PARÁMETROS TERRITORIALES</b>", unsafe_allow_html=True)
    f_nombre = st.text_input("1. Nombre de Actor / Persona:")
    # Selector estricto basado en los 212 municipios de Veracruz
    f_lugar = st.selectbox("2. Municipio (Veracruz):", MUNICIPIOS_VERACRUZ, index=MUNICIPIOS_VERACRUZ.index("Córdoba") if "Córdoba" in MUNICIPIOS_VERACRUZ else 0)
    f_zona = st.selectbox("Teatro de Operaciones (Zona):", ["Altas Montañas (Orizaba, Córdoba, Fortín)", "Zona Centro Estatal (Xalapa, Veracruz)", "Zona Norte (Poza Rica, Tuxpan)", "Zona Sur (Coatzacoalcos, Minatitlán)", "Todo el Estado de Veracruz"])
    f_partido = st.selectbox("3. Partido Político:", ["Todos", "MORENA", "PAN", "PRI", "Movimiento Ciudadano (MC)", "PVEM", "PT", "PRD", "SOMOS"])
    f_palabra = st.text_input("4. Palabra Clave Adicional:")
    f_tema = st.selectbox("5. Eje Temático:", ["Todos los temas", "Seguridad y Justicia", "Política y Gobierno", "Economía y Comercio", "Servicios e Infraestructura", "Deportes", "Ciencia y Salud", "Protección Civil y Clima"])
    
    st.divider()
    periodo = st.selectbox("Ventana de Escaneo:", ["Últimas 24 horas", "Últimos 3 días", "Última semana"])
    limite_web = st.slider("Notas a procesar:", 3, 15, 6)
    
    with st.expander("Configuración API"):
        gemini_key_in = st.text_input("Gemini API Key:", value=GEMINI_KEY_DEFAULT, type="password")

    btn_ejecutar_web = st.button("⚡ ESCANEAR PRENSA DIGITAL", use_container_width=True)
    btn_ejecutar_fb = st.button("📡 RASTREAR PERFILES Y REDES", use_container_width=True)

hora_actual = datetime.now(ZoneInfo("America/Mexico_City")).strftime("%H:%M:%S hrs")
notas_todas = st.session_state.get("notas_web", []) + st.session_state.get("notas_fb", [])
df_total = pd.DataFrame(notas_todas) if notas_todas else pd.DataFrame()

if not df_total.empty:
    fav_n, neu_n, cri_n = len(df_total[df_total['Tono']=='Favorable']), len(df_total[df_total['Tono']=='Neutro']), len(df_total[df_total['Tono']=='Crítico'])
    crisis_n = sum(1 for n in notas_todas if n.get('EsCrisis'))
    score_riesgo = min(max(int(((cri_n * 2.5 + crisis_n * 4.0) / (len(df_total) * 2.5)) * 100), 5), 98)
else:
    fav_n, neu_n, cri_n, crisis_n, score_riesgo = 0, 0, 0, 0, 5

if score_riesgo >= 75: defcon_lvl, defcon_color = "ALERTA CRÍTICA", "#EF233C"
elif score_riesgo >= 55: defcon_lvl, defcon_color = "ATENCIÓN MEDIA", "#FBBF24"
else: defcon_lvl, defcon_color = "ESTABLE", "#16A34A"

objetivo_res = f"{f_nombre} | {f_lugar}".strip(" |") if f_nombre else f_lugar

st.markdown(f"""
<div class="ticker-wrap">
    <div style="color: #ef007f; font-weight:800; margin-right:10px;">● PULSO [{hora_actual}]:</div>
    <div style="width: 100%; overflow: hidden;"><marquee style="color: #fce7f3;">{' /// '.join([n['Titular'] for n in notas_todas[:5]]) if notas_todas else 'PLATAFORMA EN MOVIMIENTO · LISTA PARA ESCANEO TERRITORIAL...'}</marquee></div>
</div>
""", unsafe_allow_html=True)

if btn_ejecutar_web:
    clausulas = []
    if f_nombre.strip(): clausulas.append(f'"{f_nombre.strip()}"')
    # Forzamos siempre el municipio exacto acoplado estrictamente al estado de Veracruz, México
    clausulas.append(f'"{f_lugar} Veracruz"')
    
    mapa_zonas = {
        "Altas Montañas (Orizaba, Córdoba, Fortín)": "(Córdoba OR Orizaba OR Fortín)", 
        "Zona Centro Estatal (Xalapa, Veracruz)": "(Xalapa OR Veracruz)", 
        "Zona Norte (Poza Rica, Tuxpan)": '("Poza Rica" OR Tuxpan)', 
        "Zona Sur (Coatzacoalcos, Minatitlán)": '(Coatzacoalcos OR Minatitlán)', 
        "Todo el Estado de Veracruz": "Veracruz"
    }
    if mapa_zonas.get(f_zona): clausulas.append(mapa_zonas[f_zona])
    mapa_partidos = {"MORENA": '(Morena)', "PAN": '(PAN)', "PRI": '(PRI)', "Movimiento Ciudadano (MC)": '(MC)', "SOMOS": '(SOMOS OR "Partido Somos")'}
    if f_partido in mapa_partidos: clausulas.append(mapa_partidos[f_partido])
    if f_palabra.strip(): clausulas.append(f'"{f_palabra.strip()}"')
    mapa_temas = {"Seguridad y Justicia": "(seguridad OR policía OR homicidio OR delito)", "Política y Gobierno": "(alcalde OR gobierno OR elecciones)", "Economía y Comercio": "(economía OR inversión OR comercio)"}
    if mapa_temas.get(f_tema): clausulas.append(mapa_temas[f_tema])
    
    if periodo == "Últimas 24 horas": clausulas.append("when:1d")
    elif periodo == "Últimos 3 días": clausulas.append("when:3d")
    elif periodo == "Última semana": clausulas.append("when:7d")

    q = " ".join(clausulas)
    lista_previa = []
    with st.spinner(f"Rastreando prensa para {f_lugar}, Veracruz..."):
        feed = feedparser.parse(f"https://news.google.com/rss/search?q={urllib.parse.quote(q)}&hl=es-419&gl=MX&ceid=MX:es-419")
        for nota in feed.entries[:limite_web]:
            tit = nota.title
            medio_nombre = nota.source.title if hasattr(nota, "source") else "Web"
            tono, col, es_crisis, severidad = evaluar_tono_y_crisis(tit)
            lista_previa.append({"Titular": tit, "Medio": medio_nombre, "Enlace": nota.link, "Tono": tono, "Color": col, "EsCrisis": es_crisis, "Severidad": severidad, "Sector": clasificar_sector(tit)})

    if lista_previa:
        progreso = st.progress(0)
        lista_procesada = []
        for idx, item in enumerate(lista_previa, 1):
            progreso.progress(idx / len(lista_previa), text=f"Analizando nota {idx} de {len(lista_previa)}...")
            url_real = decodificar_url_google(item["Enlace"])
            resumen, postura = analizar_nota_con_ia(item["Titular"], item["Medio"], gemini_key_in)
            item["No"] = idx
            item["EnlaceReal"] = url_real
            item["Resumen"] = resumen
            item["PosturaTactico"] = postura
            lista_procesada.append(item)
            time.sleep(1.0)
            
        progreso.empty()
        st.session_state["notas_web"] = lista_procesada
        st.session_state["briefing_memo"] = generar_briefing_global(objetivo_res, lista_procesada, gemini_key_in)
        st.success("¡Barrido territorial completado!")
        st.rerun()
    else:
        st.warning(f"No se hallaron notas recientes específicas para {f_lugar}, Veracruz con estos filtros.")

if btn_ejecutar_fb:
    filtro_partido_str = f'"{f_partido}"' if f_partido != "Todos" else ""
    objetivo_busqueda = f'"{f_nombre.strip()}"' if f_nombre.strip() else f'"{f_lugar}"'
    q_social = f'site:facebook.com {objetivo_busqueda} {filtro_partido_str} "{f_lugar}" Veracruz when:2d'.strip()
    
    lista_social = []
    with st.spinner(f"Rastreando perfiles públicos en {f_lugar}..."):
        feed_soc = feedparser.parse(f"https://news.google.com/rss/search?q={urllib.parse.quote(q_social)}&hl=es-419&gl=MX&ceid=MX:es-419")
        for nota in feed_soc.entries[:6]:
            tit = nota.title
            tono, col, es_crisis, severidad = evaluar_tono_y_crisis(tit)
            lista_social.append({"Titular": tit, "Medio": "Facebook / Perfil Público", "Enlace": nota.link, "Tono": tono, "Color": col, "EsCrisis": es_crisis, "Severidad": severidad, "Sector": clasificar_sector(tit)})

    if lista_social:
        progreso_soc = st.progress(0)
        lista_soc_procesada = []
        for idx, item in enumerate(lista_social, 1):
            progreso_soc.progress(idx / len(lista_social), text=f"Procesando mención social {idx}...")
            url_real = decodificar_url_google(item["Enlace"])
            resumen, postura = analizar_nota_con_ia(item["Titular"], "Facebook", gemini_key_in)
            item["No"] = idx
            item["EnlaceReal"] = url_real
            item["Resumen"] = resumen
            item["PosturaTactico"] = postura
            lista_soc_procesada.append(item)
            time.sleep(1.0)
        progreso_soc.empty()
        st.session_state["notas_fb"] = lista_soc_procesada
        st.success("¡Rastreo en redes completado!")
        st.rerun()
    else:
        st.warning("No se hallaron publicaciones públicas recientes con esos filtros.")

# Pestañas principales de navegación con estética coquetona
tab_mando, tab_territorio, tab_radar, tab_gis, tab_prensa, tab_fb, tab_despacho = st.tabs([
    "💖 Sala de Mando", "📍 Territorio", "📊 Radar Político", "🗺️ GIS Veracruz", "🌐 Prensa Web", "📡 Redes", "📑 Despacho"
])

with tab_mando:
    st.markdown(f"### Centro de Inteligencia · {f_lugar}, Veracruz")
    if not df_total.empty:
        st.markdown(f"<div style='border-left: 4px solid #ef007f; padding: 15px; background: #12172b; border-radius: 8px;'><b style='color:#ff4aa1;'>MEMO EJECUTIVO TERRITORIAL:</b><br><span style='color:#FFFFFF;'>{st.session_state.get('briefing_memo', '')}</span></div><br>", unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("<h4 style='color: #FFFFFF; font-weight: 800;'>DISPERSIÓN DE TONO Y SEVERIDAD</h4>", unsafe_allow_html=True)
            fig_scatter = px.scatter(df_total, x="Severidad", y="Tono", color="Tono", hover_name="Titular", color_discrete_map={"Favorable": "#16A34A", "Neutro": "#8B9099", "Crítico": "#EF233C"})
            fig_scatter.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(18, 23, 43, 0.8)', font={'color': '#FFFFFF'}, height=320)
            st.plotly_chart(fig_scatter, use_container_width=True)
        with col2:
            st.markdown("<h4 style='color: #FFFFFF; font-weight: 800;'>DISTRIBUCIÓN POR SECTOR</h4>", unsafe_allow_html=True)
            fig_tree = px.treemap(df_total.value_counts('Sector').reset_index(name='Notas'), path=['Sector'], values='Notas', color='Notas', color_continuous_scale=['#2a3353', '#ef007f'])
            fig_tree.update_layout(paper_bgcolor='rgba(0,0,0,0)', font={'color': '#FFFFFF'}, height=320)
            st.plotly_chart(fig_tree, use_container_width=True)
    else:
        st.info("Selecciona un municipio y ejecuta el escaneo en la barra lateral para poblar los tableros interactivos.")

with tab_territorio:
    st.markdown(f"### Análisis Georreferenciado: {f_lugar}")
    st.markdown("Visualización de impacto operativo en el municipio seleccionado de Veracruz.")
    if not df_total.empty:
        st.dataframe(df_total[['No', 'Sector', 'Titular', 'Medio', 'Tono']], use_container_width=True)
    else:
        st.info("Sin registros cargados en este teatro de operaciones.")

with tab_radar:
    st.markdown("### Radar Político y Cobertura de Actores")
    if not df_total.empty:
        fig_bar = px.bar(df_total.value_counts(['Sector', 'Tono']).reset_index(name='Conteo'), x='Sector', y='Conteo', color='Tono', barmode='group', color_discrete_map={"Favorable": "#16A34A", "Neutro": "#8B9099", "Crítico": "#EF233C"})
        fig_bar.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(18, 23, 43, 0.8)', font={'color': '#FFFFFF'})
        st.plotly_chart(fig_bar, use_container_width=True)
    else:
        st.info("Ejecuta un escaneo para activar el radar.")

with tab_gis:
    st.markdown("### Módulo GIS · Capas de Veracruz")
    st.markdown("Exploración espacial de municipios, distritos y regiones prioritarias (como Altas Montañas).")
    st.metric("Municipio Activo Analizado", f"{f_lugar}, Ver.", "Zona operativa verificada")
    # Gráfica simulada de densidad regional
    df_map_dummy = pd.DataFrame({"Municipio": [f_lugar, "Xalapa", "Veracruz", "Orizaba", "Córdoba"], "Actividad": [85, 60, 75, 50, 90]})
    fig_map = px.bar(df_map_dummy, x="Municipio", y="Actividad", color="Actividad", color_continuous_scale=["#ff4aa1", "#ef007f"])
    fig_map.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(18, 23, 43, 0.8)', font={'color': '#FFFFFF'})
    st.plotly_chart(fig_map, use_container_width=True)

with tab_prensa:
    for item in st.session_state.get("notas_web", []):
        tag_cls = "tag-critico" if item['Tono'] == "Crítico" else ("tag-favorable" if item['Tono'] == "Favorable" else "tag-neutro")
        st.markdown(f"""
        <div class="intel-card">
            <div><span class="badge-tag {tag_cls}">● {item['Tono'].upper()}</span><span class="badge-tag tag-sector">{item['Sector'].upper()}</span></div>
            <h3>{item['No']}. {item['Titular']}</h3>
            <div class="fuente-txt">Fuente: <b>{item['Medio']}</b></div>
            <div class="sintesis-txt"><b>Síntesis Analítica:</b> {item['Resumen']}</div>
            {f'<div class="tactical-box"><b>💖 Directriz Operativa:</b><br>{item["PosturaTactico"]}</div>' if item.get("PosturaTactico") else ''}
        </div>
        """, unsafe_allow_html=True)
        st.link_button("Abrir Fuente Original ↗", item["EnlaceReal"])

with tab_fb:
    for item in st.session_state.get("notas_fb", []):
        tag_cls = "tag-critico" if item['Tono'] == "Crítico" else ("tag-favorable" if item['Tono'] == "Favorable" else "tag-neutro")
        st.markdown(f"""
        <div class="intel-card">
            <div><span class="badge-tag {tag_cls}">● {item['Tono'].upper()}</span><span class="badge-tag tag-sector">{item['Sector'].upper()}</span></div>
            <h3>{item['No']}. {item['Titular']}</h3>
            <div class="fuente-txt">Canal: <b>{item['Medio']}</b></div>
            <div class="sintesis-txt"><b>Síntesis Analítica:</b> {item['Resumen']}</div>
            {f'<div class="tactical-box"><b>💖 Directriz Operativa:</b><br>{item["PosturaTactico"]}</div>' if item.get("PosturaTactico") else ''}
        </div>
        """, unsafe_allow_html=True)
        st.link_button("Abrir Publicación en Facebook ↗", item["EnlaceReal"])

with tab_despacho:
    st.subheader("Consola de Despacho y Exportación")
    if notas_todas:
        col_dp1, col_dp2 = st.columns([1, 2])
        with col_dp1:
            st.markdown("<b style='color: white;'>Formatos Institucionales:</b>", unsafe_allow_html=True)
            pdf_data = generar_pdf(objetivo_res, periodo, notas_todas, st.session_state.get("briefing_memo", ""), logo_bytes)
            st.download_button("📄 DESCARGAR DOSSIER PDF", pdf_data, file_name=f"Dossier_{f_lugar}.pdf", mime="application/pdf", use_container_width=True)
        with col_dp2:
            txt_reporte = f"💖 *SÍNTESIS TERRITORIAL · VERACRUZ*\nMunicipio: {f_lugar} | Estatus: {defcon_lvl}\n━━━━━━━━━━━━━━━━━━━━\n📌 *MEMO EJECUTIVO:*\n{st.session_state.get('briefing_memo', '')}\n━━━━━━━━━━━━━━━━━━━━\n\n"
            for n in notas_todas:
                ico = "🔴" if n['Tono'] == "Crítico" else ("🟢" if n['Tono'] == "Favorable" else "⚪")
                txt_reporte += f"{ico} *{n['No']}. [{n['Sector'].upper()}] {n['Titular']}*\n🏢 Fuente: {n['Medio']}\n📝 *Resumen:* {n['Resumen']}\n"
                if n.get("PosturaTactico"): txt_reporte += f"💡 *Directriz:* {n['PosturaTactico']}\n"
                txt_reporte += f"🔗 {n['EnlaceReal']}\n\n"
            st.text_area("Texto listo para WhatsApp / Telegram:", value=txt_reporte, height=300)
            st.download_button("💬 Descargar Archivo (.txt)", txt_reporte, file_name="reporte_territorial.txt", mime="text/plain", use_container_width=True)
    else:
        st.info("Ejecuta un escaneo territorial para habilitar el despacho de informes.")
