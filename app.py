import streamlit as st
import feedparser
import urllib.parse
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from email.utils import parsedate_to_datetime
import io
import time
import requests
import json
import re
from bs4 import BeautifulSoup
from googlenewsdecoder import gnewsdecoder

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable, Image as RLImage

st.set_page_config(page_title="WAR ROOM | Centro Táctico", page_icon="🛡️", layout="wide")

GEMINI_KEY_DEFAULT = "AQ.Ab8RN6IuER73mlESZCyQUHz8A8f5Ze7gwrSR1S8YZHdEGPFi6g"
URL_LOGO = "https://lh3.googleusercontent.com/d/1Q7A8-14SevxaLSmrzsDZDQDArpQKkvhh"

@st.cache_data(show_spinner=False)
def descargar_logo(url):
    try:
        resp = requests.get(url, timeout=5)
        if resp.status_code == 200: return resp.content
    except: pass
    return None

logo_bytes = descargar_logo(URL_LOGO)

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700;800&family=Inter:wght@400;600;800;900&display=swap');
    
    .stApp { background-color: #050811 !important; color: #FFFFFF !important; font-family: 'Inter', sans-serif !important; }
    [data-testid="stSidebar"] { background-color: #0A0F1D !important; border-right: 1px solid #1E293B !important; }
    
    .stTextInput label p, .stSelectbox label p, .stSlider label p { color: #FFFFFF !important; font-weight: 700 !important; font-size: 0.95rem !important; }
    
    .ticker-wrap { width: 100%; overflow: hidden; background-color: #090E1A; border: 1px solid #1E293B; border-radius: 6px; padding: 8px 12px; margin-bottom: 20px; font-family: 'JetBrains Mono', monospace; font-size: 0.85rem; display: flex; align-items: center; }
    
    .defcon-card { background: linear-gradient(180deg, rgba(15, 23, 42, 0.95) 0%, rgba(10, 15, 29, 0.95) 100%); border-radius: 8px; padding: 16px; border: 1px solid #1E293B; text-align: center; box-shadow: 0 4px 20px rgba(0,0,0,0.5); }
    .defcon-1 { border-top: 4px solid #EF4444; } .defcon-2 { border-top: 4px solid #F97316; } .defcon-3 { border-top: 4px solid #EAB308; } .defcon-4 { border-top: 4px solid #06B6D4; } .defcon-5 { border-top: 4px solid #10B981; }
    
    .intel-card { background: linear-gradient(180deg, #0A0F1D 0%, #060913 100%); border: 1px solid #1E293B; border-radius: 8px; padding: 20px; margin-bottom: 18px; color: #FFFFFF !important; }
    .intel-card h3 { color: #FFFFFF !important; font-size: 1.15rem; margin-top: 10px; margin-bottom: 5px; }
    .intel-card b { color: #F8FAFC !important; }
    .intel-card .fuente-txt { color: #F1F5F9 !important; font-size: 0.85rem; margin-bottom: 12px; }
    .intel-card .sintesis-txt { color: #FFFFFF !important; font-size: 1rem; line-height: 1.6; margin-bottom: 10px; }
    
    .badge-tag { font-family: 'JetBrains Mono', monospace; font-size: 0.7rem; font-weight: 700; padding: 3px 8px; border-radius: 4px; display: inline-block; margin-right: 6px; }
    .tag-critico { background: rgba(239, 68, 68, 0.2); color: #F87171; border: 1px solid rgba(239, 68, 68, 0.5); }
    .tag-neutro { background: rgba(148, 163, 184, 0.2); color: #E2E8F0; border: 1px solid rgba(148, 163, 184, 0.5); }
    .tag-favorable { background: rgba(16, 185, 129, 0.2); color: #34D399; border: 1px solid rgba(16, 185, 129, 0.5); }
    .tag-sector { background: rgba(56, 189, 248, 0.15); color: #38BDF8; border: 1px solid rgba(56, 189, 248, 0.4); }
    
    .tactical-box { background-color: #030712; border-left: 3px solid #F59E0B; padding: 12px 14px; border-radius: 0 6px 6px 0; font-size: 0.9rem; color: #FDE68A; margin-top: 12px; line-height: 1.5; }
    div.stButton > button:first-child { background: linear-gradient(135deg, #E11D48 0%, #9F1239 100%) !important; color: #FFFFFF !important; border: 1px solid #FB7185 !important; border-radius: 6px !important; font-weight: 800 !important; font-family: 'JetBrains Mono', monospace !important; padding: 0.6rem 1.4rem !important; }
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
        modelos = ["gemini-3.6-flash", "gemini-2.5-flash", "gemini-2.0-flash"]
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
    if any(v in t for v in veto_crisis): return "Crítico", "#EF4444", True, 10
    detonantes = ["denuncia penal", "fraude", "desvío", "bloqueo", "paro", "protesta", "colapso", "renuncia", "corrupción", "amenaza", "heridos"]
    criticas = ["queja", "exigen", "falla", "falta", "inseguridad", "robo", "violencia", "accidente", "crisis", "alerta", "cae"]
    favorables = ["inaugura", "avance", "inversión", "apoyo", "mejora", "beneficio", "obra", "anuncian", "entrega", "logro", "lidera"]
    
    es_crisis = any(d in t for d in detonantes)
    s_crit = sum(1 for p in (detonantes + criticas) if p in t)
    s_fav = sum(1 for p in favorables if p in t)
    
    if es_crisis: return "Crítico", "#EF4444", True, 9
    elif s_crit > s_fav: return "Crítico", "#EF4444", False, 7
    elif s_fav > s_crit: return "Favorable", "#10B981", False, 2
    return "Neutro", "#94A3B8", False, 4

def generar_briefing_global(termino, lista_notas, gemini_k):
    if not lista_notas: return "Panorama Informativo: Monitoreo estratégico procesado."
    corpus = "\n".join([f"- [{n['Tono']}] {n['Titular']} ({n['Medio']})" for n in lista_notas[:8]])
    prompt = f"Objetivo: '{termino}'. Basado en estos reportes:\n{corpus}\n\nRedacta un Memo de Situación ejecutivo en un párrafo fluido de 4 líneas que resuma el pulso político y social actual. PROHIBIDO USAR PARÉNTESIS."
    resultado = consultar_llm_dual(prompt, gemini_k)
    return resultado.replace("(", "").replace(")", "") if resultado else "Cobertura distribuida sin incidencias críticas en la demarcación."

def analizar_nota_con_ia(titular, medio, gemini_k):
    prompt = f"""Eres un analista político y periodista de gabinete experto en el estado de Veracruz. 
A partir del siguiente encabezado o mención pública reciente de la fuente '{medio}':

"{titular}"

REGLAS ESTRICTAS DE REDACCIÓN:
1. DESARROLLA UN TEXTO SÓLIDO de 4 a 5 líneas bien estructuradas. Explica con claridad meridiana qué trasfondo tiene este suceso, qué actores o fuerzas políticas intervienen y qué implicaciones o lectura política deja para la región.
2. NO USES PARÉNTESIS en ninguna parte de tu redacción.
3. PROHIBIDO usar lenguaje burocrático o frases vacías como "se da cuenta de", "en relación con" o "cobertura informativa señala". Ve directo al fondo del asunto con rigor analítico.
4. Si involucra crisis, conflicto o seguridad, define una directriz institucional de vocería clara. Si es favorable o neutral, pon N/A.

Formato exacto de respuesta:
RESUMEN: [Párrafo analítico robusto y completo de 4 a 5 líneas, CERO paréntesis, CERO relleno]
VOCERIA: [Directriz institucional o N/A]"""

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
        resumen = f"El reporte reciente detectado en torno a {titular} moviliza la atención de los usuarios y actores sociales en la demarcación. Este tipo de discusiones configuran la percepción ciudadana y marcan la pauta en la conversación digital regional."

    return resumen.replace("(", "").replace(")", ""), (postura.replace("(", "").replace(")", "") if postura and postura.upper() != "N/A" else "")

def generar_pdf(termino, periodo, lista_notas, briefing, logo_data):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    styles = getSampleStyleSheet()
    style_tit = ParagraphStyle('T1', fontName='Helvetica-Bold', fontSize=13, leading=17, textColor=colors.HexColor('#0F172A'))
    style_sub = ParagraphStyle('T2', fontName='Helvetica', fontSize=8, leading=11, textColor=colors.HexColor('#475569'))
    style_briefing = ParagraphStyle('TB', fontName='Helvetica-Oblique', fontSize=8.5, leading=12, textColor=colors.HexColor('#BE123C'))
    style_item_t = ParagraphStyle('IT', fontName='Helvetica-Bold', fontSize=9, leading=12, textColor=colors.HexColor('#0F172A'))
    style_item_m = ParagraphStyle('IM', fontName='Helvetica-Oblique', fontSize=7.5, leading=10, textColor=colors.HexColor('#64748B'))
    style_item_r = ParagraphStyle('IR', fontName='Helvetica', fontSize=8, leading=12, textColor=colors.HexColor('#334155'))
    style_item_p = ParagraphStyle('IP', fontName='Helvetica-Bold', fontSize=7.5, leading=10, textColor=colors.HexColor('#0284C7'))
    
    story = []
    fecha_emision = datetime.now(ZoneInfo("America/Mexico_City")).strftime("%d/%m/%Y - %H:%M hrs")
    cabecera = [RLImage(io.BytesIO(logo_data), width=45, height=45)] if logo_data else [""]
    cabecera.append([Paragraph("<b>SÍNTESIS ESTRATÉGICA DE INTELIGENCIA</b>", style_tit), Paragraph(f"Objetivo: <b>{termino}</b> &nbsp;|&nbsp; Rango: <b>{periodo}</b> &nbsp;|&nbsp; Emisión: {fecha_emision}", style_sub)])
    story.append(Table([cabecera], colWidths=[52, 488]))
    story.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor('#F43F5E'), spaceAfter=8))
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
    else: st.markdown("<h2 style='color: #F43F5E;'>WAR ROOM</h2>", unsafe_allow_html=True)
    st.divider()

    st.markdown("<b style='color: #FFFFFF;'>PARÁMETROS DE INTELIGENCIA</b>", unsafe_allow_html=True)
    f_nombre = st.text_input("1. Nombre de Persona:")
    f_lugar = st.text_input("2. Municipio Específico:", value="Córdoba")
    f_zona = st.selectbox("Teatro de Operaciones (Zona):", ["Córdoba - Fortín (Hiperlocal)", "Altas Montañas (Orizaba, Córdoba, Huatusco)", "Zona Centro Estatal (Xalapa, Veracruz)", "Zona Norte (Poza Rica, Tuxpan)", "Zona Sur (Coatzacoalcos, Minatitlán)", "Todo el Estado de Veracruz", "Nacional (Todo México)"])
    f_partido = st.selectbox("3. Partido Político:", ["Todos", "MORENA", "PAN", "PRI", "Movimiento Ciudadano (MC)", "PVEM", "PT", "PRD", "SOMOS"])
    f_palabra = st.text_input("4. Palabra Clave:")
    f_tema = st.selectbox("5. Eje Temático:", ["Todos los temas", "Seguridad y Justicia", "Política y Gobierno", "Economía y Comercio", "Servicios e Infraestructura", "Deportes", "Ciencia y Salud", "Protección Civil y Clima"])
    
    st.divider()
    periodo = st.selectbox("Ventana de Escaneo:", ["Últimas 24 horas", "Últimos 3 días", "Última semana"])
    limite_web = st.slider("Notas a procesar:", 3, 15, 6)
    
    with st.expander("Claves API"):
        gemini_key_in = st.text_input("Gemini API Key:", value=GEMINI_KEY_DEFAULT, type="password")

    btn_ejecutar_web = st.button("⚡ ESCANEAR PRENSA DIGITAL", use_container_width=True)
    btn_ejecutar_fb = st.button("📡 RASTREAR OPINIÓN Y REDES (ESTRICTO)", use_container_width=True)

hora_actual = datetime.now(ZoneInfo("America/Mexico_City")).strftime("%H:%M:%S hrs")
notas_todas = st.session_state.get("notas_web", []) + st.session_state.get("notas_fb", [])
df_total = pd.DataFrame(notas_todas) if notas_todas else pd.DataFrame()

if not df_total.empty:
    fav_n, neu_n, cri_n = len(df_total[df_total['Tono']=='Favorable']), len(df_total[df_total['Tono']=='Neutro']), len(df_total[df_total['Tono']=='Crítico'])
    crisis_n = sum(1 for n in notas_todas if n.get('EsCrisis'))
    score_riesgo = min(max(int(((cri_n * 2.5 + crisis_n * 4.0) / (len(df_total) * 2.5)) * 100), 5), 98)
else:
    fav_n, neu_n, cri_n, crisis_n, score_riesgo = 0, 0, 0, 0, 5

if score_riesgo >= 75: defcon_lvl, defcon_class, defcon_color = "DEFCON 1", "defcon-1", "#EF4444"
elif score_riesgo >= 55: defcon_lvl, defcon_class, defcon_color = "DEFCON 2", "defcon-2", "#F97316"
else: defcon_lvl, defcon_class, defcon_color = "DEFCON 5", "defcon-5", "#10B981"

objetivo_res = f"{f_nombre} | {f_lugar}".strip(" |") if f_nombre else f_lugar

st.markdown(f"""
<div class="ticker-wrap" style="border-left: 4px solid {defcon_color};">
    <div class="ticker-title" style="color: {defcon_color};">● RADAR [{hora_actual}]:</div>
    <div class="ticker-content"><marquee>{' /// '.join([n['Titular'] for n in notas_todas[:5]]) if notas_todas else 'ESPERANDO ÓRDENES...'}</marquee></div>
</div>
""", unsafe_allow_html=True)

if btn_ejecutar_web:
    clausulas = []
    if f_nombre.strip(): clausulas.append(f'"{f_nombre.strip()}"')
    if f_lugar.strip(): clausulas.append(f'"{f_lugar.strip()}"')
    mapa_zonas = {"Córdoba - Fortín (Hiperlocal)": "(Córdoba OR Fortín)", "Altas Montañas (Orizaba, Córdoba, Huatusco)": "(Córdoba OR Orizaba OR Huatusco)", "Zona Centro Estatal (Xalapa, Veracruz)": "(Xalapa OR Veracruz)", "Zona Norte (Poza Rica, Tuxpan)": '("Poza Rica" OR Tuxpan)', "Zona Sur (Coatzacoalcos, Minatitlán)": '(Coatzacoalcos OR Minatitlán)', "Todo el Estado de Veracruz": "Veracruz"}
    if mapa_zonas.get(f_zona): clausulas.append(mapa_zonas[f_zona])
    mapa_partidos = {"MORENA": '(Morena)', "PAN": '(PAN)', "PRI": '(PRI)', "Movimiento Ciudadano (MC)": '(MC)', "SOMOS": '(SOMOS OR "Partido Somos")'}
    if f_partido in mapa_partidos: clausulas.append(mapa_partidos[f_partido])
    if f_palabra.strip(): clausulas.append(f'"{f_palabra.strip()}"')
    mapa_temas = {"Seguridad y Justicia": "(seguridad OR policía OR homicidio OR delito)", "Política y Gobierno": "(alcalde OR gobierno OR elecciones)", "Economía y Comercio": "(economía OR inversión OR comercio)"}
    if mapa_temas.get(f_tema): clausulas.append(mapa_temas[f_tema])
    clausulas.append("Veracruz")
    if periodo == "Últimas 24 horas": clausulas.append("when:1d")
    elif periodo == "Últimos 3 días": clausulas.append("when:3d")
    elif periodo == "Última semana": clausulas.append("when:7d")

    q = " ".join(clausulas)
    lista_previa = []
    with st.spinner("Rastreando fuentes periodísticas..."):
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
            progreso.progress(idx / len(lista_previa), text=f"Analizando nota estratégica {idx} de {len(lista_previa)}...")
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
        st.success("¡Barrido de prensa completado!")
        st.rerun()
    else:
        st.warning("No se hallaron notas con esos filtros.")

if btn_ejecutar_fb:
    # Búsqueda estricta obligatoria para el nombre y el municipio (sin desviarse)
    termino_social = f'"{f_nombre.strip()}"' if f_nombre.strip() else f'"{f_lugar}"'
    q_social = f'{termino_social} (Veracruz OR Córdoba) when:2d'
    
    lista_social = []
    with st.spinner("Rastreando menciones estrictas recientes..."):
        feed_soc = feedparser.parse(f"https://news.google.com/rss/search?q={urllib.parse.quote(q_social)}&hl=es-419&gl=MX&ceid=MX:es-419")
        for nota in feed_soc.entries[:6]:
            tit = nota.title
            medio_nombre = nota.source.title if hasattr(nota, "source") else "Opinión / Redes"
            tono, col, es_crisis, severidad = evaluar_tono_y_crisis(tit)
            lista_social.append({"Titular": tit, "Medio": f"Mención: {medio_nombre}", "Enlace": nota.link, "Tono": tono, "Color": col, "EsCrisis": es_crisis, "Severidad": severidad, "Sector": clasificar_sector(tit)})

    if lista_social:
        progreso_soc = st.progress(0)
        lista_soc_procesada = []
        for idx, item in enumerate(lista_social, 1):
            progreso_soc.progress(idx / len(lista_social), text=f"Analizando mención digital {idx}...")
            url_real = decodificar_url_google(item["Enlace"])
            resumen, postura = analizar_nota_con_ia(item["Titular"], item["Medio"], gemini_key_in)
            item["No"] = idx
            item["EnlaceReal"] = url_real
            item["Resumen"] = resumen
            item["PosturaTactico"] = postura
            lista_soc_procesada.append(item)
            time.sleep(1.0)
        progreso_soc.empty()
        st.session_state["notas_fb"] = lista_soc_procesada
        st.success("¡Rastreo estricto completado!")
        st.rerun()
    else:
        st.warning("No se hallaron menciones recientes exactas con ese nombre en las últimas 48 horas.")

tab_mando, tab_prensa, tab_fb, tab_despacho = st.tabs(["🎯 Sala de Mando", "🌐 Prensa Web", "📡 Opinión y Redes", "📑 Despacho de Informes"])

with tab_mando:
    if not df_total.empty:
        st.markdown(f"<div style='border-left: 4px solid #38BDF8; padding: 15px; background: #0A0F1D; border-radius: 6px;'><b style='color:#38BDF8;'>MEMO EJECUTIVO:</b><br><span style='color:#FFFFFF;'>{st.session_state.get('briefing_memo', '')}</span></div><br>", unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("<h4 style='color: #FFFFFF; font-family: monospace;'>RADAR DE AMENAZAS</h4>", unsafe_allow_html=True)
            fig_scatter = px.scatter(df_total, x="Severidad", y="Tono", color="Tono", hover_name="Titular", color_discrete_map={"Favorable": "#10B981", "Neutro": "#64748B", "Crítico": "#EF4444"})
            fig_scatter.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(6, 9, 19, 0.8)', font={'color': '#FFFFFF'}, height=320)
            st.plotly_chart(fig_scatter, use_container_width=True)
        with col2:
            st.markdown("<h4 style='color: #FFFFFF; font-family: monospace;'>MAPA DE CALOR POR SECTOR</h4>", unsafe_allow_html=True)
            fig_tree = px.treemap(df_total.value_counts('Sector').reset_index(name='Notas'), path=['Sector'], values='Notas', color='Notas', color_continuous_scale=['#1E293B', '#F43F5E'])
            fig_tree.update_layout(paper_bgcolor='rgba(0,0,0,0)', font={'color': '#FFFFFF'}, height=320)
            st.plotly_chart(fig_tree, use_container_width=True)
    else:
        st.info("A la espera de escaneo táctico.")

with tab_prensa:
    for item in st.session_state.get("notas_web", []):
        tag_cls = "tag-critico" if item['Tono'] == "Crítico" else ("tag-favorable" if item['Tono'] == "Favorable" else "tag-neutro")
        st.markdown(f"""
        <div class="intel-card">
            <div><span class="badge-tag {tag_cls}">● {item['Tono'].upper()}</span><span class="badge-tag tag-sector">{item['Sector'].upper()}</span></div>
            <h3>{item['No']}. {item['Titular']}</h3>
            <div class="fuente-txt">Fuente: <b>{item['Medio']}</b></div>
            <div class="sintesis-txt"><b>Síntesis Analítica:</b> {item['Resumen']}</div>
            {f'<div class="tactical-box"><b>🛡️ Directriz de Vocería:</b><br>{item["PosturaTactico"]}</div>' if item.get("PosturaTactico") else ''}
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
            {f'<div class="tactical-box"><b>🛡️ Directriz Táctica:</b><br>{item["PosturaTactico"]}</div>' if item.get("PosturaTactico") else ''}
        </div>
        """, unsafe_allow_html=True)
        st.link_button("Abrir Publicación Original ↗", item["EnlaceReal"])

with tab_despacho:
    st.subheader("Consola de Despacho Operativo")
    if notas_todas:
        col_dp1, col_dp2 = st.columns([1, 2])
        with col_dp1:
            st.markdown("<b style='color: white;'>Formatos Oficiales:</b>", unsafe_allow_html=True)
            pdf_data = generar_pdf(objetivo_res, periodo, notas_todas, st.session_state.get("briefing_memo", ""), logo_bytes)
            st.download_button("📄 DESCARGAR PDF", pdf_data, file_name=f"Dossier_{objetivo_res}.pdf", mime="application/pdf", use_container_width=True)
        with col_dp2:
            txt_reporte = f"🛡️ *SÍNTESIS ESTRATÉGICA*\nObjetivo: {objetivo_res} | Estatus: {defcon_lvl}\n━━━━━━━━━━━━━━━━━━━━\n📌 *MEMO EJECUTIVO:*\n{st.session_state.get('briefing_memo', '')}\n━━━━━━━━━━━━━━━━━━━━\n\n"
            for n in notas_todas:
                ico = "🔴" if n['Tono'] == "Crítico" else ("🟢" if n['Tono'] == "Favorable" else "⚪")
                txt_reporte += f"{ico} *{n['No']}. [{n['Sector'].upper()}] {n['Titular']}*\n🏢 Fuente: {n['Medio']}\n📝 *Resumen:* {n['Resumen']}\n"
                if n.get("PosturaTactico"): txt_reporte += f"💡 *Directriz:* {n['PosturaTactico']}\n"
                txt_reporte += f"🔗 {n['EnlaceReal']}\n\n"
            st.text_area("Texto listo para WhatsApp / Telegram:", value=txt_reporte, height=300)
            st.download_button("💬 Descargar Archivo (.txt)", txt_reporte, file_name="reporte.txt", mime="text/plain", use_container_width=True)
    else:
        st.info("Ejecuta un escaneo para habilitar el centro de despacho.")
