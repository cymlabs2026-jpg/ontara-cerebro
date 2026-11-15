"""Ontara Cerebro · C&M Labs
Pregúntale a todos tus documentos y recibe respuestas con la fuente exacta.

- Modo local: lee las carpetas de tu computador (ejecutar con Iniciar_Ontara_Cerebro.bat).
- Modo demo: si existe la carpeta demo_docs junto a este archivo, la app lee solo esos
  documentos de ejemplo (así funciona la demo pública en Streamlit Community Cloud).
"""
import json
import os
import subprocess
import sys

import streamlit as st

from motor import Cerebro

APP_DIR = os.path.dirname(os.path.abspath(__file__))
DEMO_DIR = os.path.join(APP_DIR, "demo_docs")
DEMO = os.path.isdir(DEMO_DIR)
DATOS = os.path.join(APP_DIR, "datos")
CONFIG = os.path.join(DATOS, "config.json")
ARCHIVO_CLAVE = os.path.join(DATOS, "clave_api.txt")
INICIO = os.path.expanduser("~")
MAX_PREGUNTAS_DEMO = 15  # por visitante, para cuidar el saldo de la API

MODELOS = {
    "Equilibrado · Claude Sonnet 5.5": "claude-sonnet-5-5",
    "Económico y rápido · Claude Haiku 5.5": "claude-haiku-5-5",
    "Máxima calidad · Claude Opus 5.5": "claude-opus-5-5",
}
if DEMO:
    MODELOS = {"Rápido · Claude Haiku 5.5": "claude-haiku-5-5",
               "Equilibrado · Claude Sonnet 5.5": "claude-sonnet-5-5"}

INSTRUCCIONES = """Eres Ontara Cerebro, el asistente de conocimiento creado por C&M Labs.
Respondes preguntas usando ÚNICAMENTE los fragmentos de documentos que se te entregan.

Reglas:
- Responde en español claro y directo, primero la respuesta y luego los detalles.
- Después de cada dato, cita la fuente con su número entre corchetes, por ejemplo [2]. Puedes citar varias: [1][3].
- Si los fragmentos no contienen la respuesta, dilo con honestidad ("No encontré eso en los documentos") y sugiere qué buscar o qué documento podría faltar. No inventes datos.
- Si hay información contradictoria entre documentos, muéstralo y cita ambos.
- Usa listas o tablas cortas cuando ayuden a leer mejor. No repitas los fragmentos completos.
- Algunos textos vienen de OCR y pueden tener errores de lectura: interpreta con sentido común."""


# ---------------------------------------------------------------- configuración
def cargar_config():
    if DEMO:
        return {"carpetas": [DEMO_DIR], "carpeta_ocr": None, "modelo": list(MODELOS)[0]}
    predeterminadas = [os.path.join(INICIO, c) for c in ("Downloads", "Documents")
                       if os.path.isdir(os.path.join(INICIO, c))]
    config = {"carpetas": predeterminadas,
              "carpeta_ocr": os.path.join(INICIO, "Downloads", "00_Ontara_Cerebro", "textos"),
              "modelo": list(MODELOS)[0]}
    if os.path.exists(CONFIG):
        try:
            with open(CONFIG, encoding="utf-8") as f:
                config.update(json.load(f))
        except (OSError, ValueError):
            pass
    return config


def guardar_config(config):
    if DEMO:
        return
    os.makedirs(DATOS, exist_ok=True)
    with open(CONFIG, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)


def clave_del_dueno():
    """Clave configurada por el dueño: secretos de Streamlit, variable de entorno o archivo local."""
    try:
        if "ANTHROPIC_API_KEY" in st.secrets:
            return st.secrets["ANTHROPIC_API_KEY"]
    except Exception:  # sin archivo de secretos
        pass
    if os.environ.get("ANTHROPIC_API_KEY"):
        return os.environ["ANTHROPIC_API_KEY"]
    if not DEMO and os.path.exists(ARCHIVO_CLAVE):
        with open(ARCHIVO_CLAVE, encoding="utf-8") as f:
            return f.read().strip()
    return ""


def abrir(ruta):
    try:
        if sys.platform.startswith("win"):
            os.startfile(ruta)  # noqa: S606 - abre con la app predeterminada de Windows
        elif sys.platform == "darwin":
            subprocess.Popen(["open", ruta])
        else:
            subprocess.Popen(["xdg-open", ruta])
    except OSError as ex:
        st.toast(f"No se pudo abrir: {ex}")


@st.cache_resource
def obtener_cerebro():
    cerebro = Cerebro(os.path.join(DATOS, "indice.db"))
    if DEMO:  # la demo se indexa sola al arrancar
        cerebro.actualizar([DEMO_DIR])
    return cerebro


# ---------------------------------------------------------------- estilo
st.set_page_config(page_title="Ontara Cerebro · C&M Labs", page_icon="🧠", layout="wide")
st.markdown("""
<style>
  .block-container {padding-top: 3.5rem; max-width: 1100px;}
  .kicker {letter-spacing: .32em; text-transform: uppercase; font-size: .72rem;
           color: #22D3EE; font-weight: 700; margin-bottom: .2rem;}
  .titulo {font-size: 2.8rem !important; font-weight: 900; line-height: 1.05; margin: 0;}
  .titulo span {color: #22D3EE;}
  .sub {color: #94A3B8; margin-top: .4rem; margin-bottom: 1.2rem;}
  .tarjeta {background: #111827; border: 1px solid #1F2937; border-radius: 14px;
            padding: 1rem 1.2rem; margin-bottom: .8rem;}
  .tarjeta b {color: #E5E7EB;}
  .fuente-num {display:inline-block; background:#22D3EE; color:#0B0F19; border-radius:6px;
               padding:0 .45rem; font-weight:800; margin-right:.4rem;}
  .ruta {color:#64748B; font-size:.78rem;}
  .metric-n {font-size:1.6rem; font-weight:900; color:#F8FAFC;}
  .metric-l {font-size:.7rem; letter-spacing:.18em; text-transform:uppercase; color:#94A3B8;}
  .pie {color:#64748B; font-size:.75rem; margin-top:2rem;}
</style>""", unsafe_allow_html=True)

cerebro = obtener_cerebro()
if "config" not in st.session_state:
    st.session_state.config = cargar_config()
    st.session_state.mensajes = []
    st.session_state.clave = "" if DEMO else clave_del_dueno()
    st.session_state.preguntas = 0
config = st.session_state.config
if not DEMO:
    from paneles import asegurar_cargas
    asegurar_cargas(config, guardar_config)
CLAVE_DUENO = clave_del_dueno() if DEMO else ""


def clave_activa():
    return st.session_state.clave or CLAVE_DUENO


def limite_alcanzado():
    # el límite solo aplica cuando la demo usa la clave del dueño
    return DEMO and not st.session_state.clave and st.session_state.preguntas >= MAX_PREGUNTAS_DEMO


# ---------------------------------------------------------------- barra lateral
with st.sidebar:
    st.markdown('<div class="kicker">C&M LABS · ONTARA</div>', unsafe_allow_html=True)
    st.markdown("### 🧠 Ontara Cerebro")
    datos = cerebro.estadisticas()
    c1, c2 = st.columns(2)
    c1.markdown(f'<div class="metric-n">{datos["documentos"]:,}</div><div class="metric-l">documentos</div>',
                unsafe_allow_html=True)
    palabras = datos["palabras"]
    c2.markdown(f'<div class="metric-n">{palabras/1000:,.0f}k</div>' if palabras >= 1000 else
                f'<div class="metric-n">{palabras:,}</div>', unsafe_allow_html=True)
    c2.markdown('<div class="metric-l">palabras</div>', unsafe_allow_html=True)

    st.divider()
    if DEMO:
        st.info("**Demo pública.** Los documentos son de *Comercializadora El Samán S.A.S.*, "
                "una empresa ficticia creada por C&M Labs. En la versión real, Ontara Cerebro "
                "lee los documentos de tu empresa.")
        with st.expander("📂 Documentos de la demo"):
            for (ruta,) in cerebro.bd.execute("SELECT ruta FROM documentos ORDER BY ruta"):
                rel = os.path.relpath(ruta, DEMO_DIR)
                st.markdown(f"- {rel}")
    else:
        st.markdown("**Carpetas que lee el cerebro**")
        texto_carpetas = st.text_area("Una carpeta por línea", "\n".join(config["carpetas"]), height=90,
                                      label_visibility="collapsed")
        if st.button("🔄 Actualizar cerebro", width="stretch", type="primary"):
            carpetas = [c.strip().strip('"') for c in texto_carpetas.splitlines() if c.strip()]
            faltantes = [c for c in carpetas if not os.path.isdir(c)]
            if faltantes:
                st.error("No existen estas carpetas:\n\n" + "\n".join(faltantes))
            else:
                config["carpetas"] = carpetas
                guardar_config(config)
                barra = st.progress(0.0, "Revisando archivos…")
                r = cerebro.actualizar(carpetas, config.get("carpeta_ocr"),
                                       lambda p, n: barra.progress(min(p, 1.0), f"Leyendo {n[:40]}"))
                barra.empty()
                st.session_state.aviso = (f"Listo: {r['nuevos']} leídos o actualizados, {r['borrados']} retirados, "
                                          f"{r['errores']} con error (de {r['revisados']} revisados).")
                st.rerun()
        if "aviso" in st.session_state:
            st.success(st.session_state.pop("aviso"))

    st.divider()
    st.markdown("**Inteligencia**")
    config["modelo"] = st.selectbox("Modelo", list(MODELOS), index=list(MODELOS).index(config["modelo"])
                                    if config["modelo"] in MODELOS else 0, label_visibility="collapsed")
    if DEMO:
        if CLAVE_DUENO:
            restantes = max(0, MAX_PREGUNTAS_DEMO - st.session_state.preguntas)
            st.caption(f"🟢 Respuestas con Claude activadas · te quedan **{restantes}** preguntas en esta demo")
        with st.expander("¿Tienes tu propia clave de API?"):
            st.session_state.clave = st.text_input("Clave de API de Claude", value=st.session_state.clave,
                                                   type="password", help="Se usa solo durante tu visita; no se guarda.")
        if not clave_activa():
            st.caption("🟡 Modo búsqueda (sin clave de API)")
    else:
        clave = st.text_input("Clave de API de Claude", value=st.session_state.clave, type="password",
                              help="Se consigue en platform.claude.com → Settings → API keys. "
                                   "Sin clave, la app funciona en modo búsqueda.")
        recordar = st.checkbox("Recordar la clave en este equipo", value=os.path.exists(ARCHIVO_CLAVE))
        if clave != st.session_state.clave or recordar != os.path.exists(ARCHIVO_CLAVE):
            st.session_state.clave = clave
            if recordar and clave:
                os.makedirs(DATOS, exist_ok=True)
                with open(ARCHIVO_CLAVE, "w", encoding="utf-8") as f:
                    f.write(clave)
            elif not recordar and os.path.exists(ARCHIVO_CLAVE):
                os.remove(ARCHIVO_CLAVE)
            guardar_config(config)
        st.caption("🟢 Modo respuestas con Claude" if clave else "🟡 Modo búsqueda (sin clave de API)")

    st.divider()
    if st.button("🗑️ Nueva conversación", width="stretch"):
        st.session_state.mensajes = []
        st.rerun()
    if not DEMO:
        with st.expander("Áreas indexadas"):
            for area, n in datos["areas"]:
                st.markdown(f"- {area} · **{n}**")


# ---------------------------------------------------------------- funciones de respuesta
def mostrar_fuentes(fuentes, pregunta, clave_msg):
    if not fuentes:
        return
    with st.expander(f"📚 Fuentes ({len(fuentes)})", expanded=not clave_activa()):
        for i, f in enumerate(fuentes, 1):
            st.markdown(f'<span class="fuente-num">{i}</span><b>{f["nombre"]}</b><br>'
                        f'<span class="ruta">{f["carpeta"]}</span>', unsafe_allow_html=True)
            st.caption(Cerebro.resaltar(f["texto"], pregunta))
            if DEMO:
                if os.path.exists(f["ruta"]):
                    with open(f["ruta"], "rb") as archivo:
                        st.download_button("Descargar documento", archivo.read(), file_name=f["nombre"],
                                           key=f"d{clave_msg}{i}")
            else:
                a, b, _ = st.columns([1, 1, 4])
                if a.button("Abrir archivo", key=f"a{clave_msg}{i}"):
                    abrir(f["ruta"])
                if b.button("Abrir carpeta", key=f"c{clave_msg}{i}"):
                    abrir(os.path.dirname(f["ruta"]))


def preguntar_a_claude(pregunta, fuentes, historial):
    import anthropic
    contexto = "\n\n".join(
        f"[{i}] Archivo: {f['nombre']} (carpeta: {f['carpeta']})\n{f['texto']}"
        for i, f in enumerate(fuentes, 1))
    mensajes = [{"role": m["rol"], "content": m["texto"]} for m in historial[-6:]]
    while mensajes and mensajes[0]["role"] != "user":
        mensajes.pop(0)
    mensajes.append({"role": "user", "content":
                     f"Fragmentos de los documentos:\n\n{contexto}\n\n---\nPregunta: {pregunta}"})
    cliente = anthropic.Anthropic(api_key=clave_activa())
    with cliente.messages.stream(model=MODELOS[config["modelo"]], max_tokens=1200,
                                 system=INSTRUCCIONES, messages=mensajes) as flujo:
        yield from flujo.text_stream


def respuesta_sin_clave(fuentes, motivo=""):
    if not fuentes:
        return "No encontré documentos relacionados. Prueba con otras palabras clave."
    encabezado = motivo or ("**Modo búsqueda** · Estos son los documentos más relacionados con tu pregunta. "
                            "Agrega una clave de API en la barra lateral para recibir respuestas redactadas.")
    lineas = [encabezado + "\n"]
    for i, f in enumerate(fuentes, 1):
        lineas.append(f"{i}. **{f['nombre']}** — {f['carpeta']}")
    return "\n".join(lineas)


# ---------------------------------------------------------------- pantalla principal
st.markdown('<div class="kicker">C&M LABS · ONTARA</div>', unsafe_allow_html=True)
st.markdown('<div class="titulo">Ontara <span>Cerebro</span></div>', unsafe_allow_html=True)
subtitulo = ("Pregúntale a todos los documentos de una empresa. Cada respuesta te dice de qué archivo salió."
             if DEMO else "Pregúntale a todo lo que tienes guardado. Cada respuesta te dice de qué archivo salió.")
st.markdown(f'<div class="sub">{subtitulo}</div>', unsafe_allow_html=True)

if DEMO:
    EJEMPLOS = ["¿En qué horario se recibe mercancía y qué documentos piden?",
                "¿Qué decidió el comité de operaciones de octubre?",
                "¿Qué productos están por debajo del stock mínimo?",
                "¿Cómo evolucionó el OTIF en 2026 frente a la meta?",
                "¿Cuál es el plazo para devolver producto refrigerado?",
                "¿Qué clientes tienen cartera vencida a más de 60 días?"]
else:
    EJEMPLOS = ["¿Qué fechas tiene el retiro de Emaús?", "Resúmeme lo que tengo sobre teoría de la burocracia",
                "¿Qué es el slotting y dónde lo explico?", "¿Qué documentos tengo sobre finanzas personales?"]

if DEMO:
    tab_chat, tab_panel = st.tabs(["💬 Preguntar", "📊 Panel"])
    tab_cargar = tab_gestion = None
else:
    tab_chat, tab_cargar, tab_gestion, tab_panel = st.tabs(
        ["💬 Preguntar", "📥 Cargar", "🗂️ Gestionar", "📊 Panel"])

with tab_chat:
    if datos["documentos"] == 0:
        st.markdown('<div class="tarjeta"><b>Bienvenido 👋</b><br>Revisa las carpetas en la barra lateral y '
                    'pulsa <b>Actualizar cerebro</b> para que lea tus documentos por primera vez. '
                    'Según cuántos tengas, puede tardar unos minutos.</div>', unsafe_allow_html=True)
    elif not st.session_state.mensajes:
        st.markdown("**Prueba con preguntas como:**")
        cols = st.columns(2)
        for i, e in enumerate(EJEMPLOS):
            if cols[i % 2].button(e, key=f"ej{i}", width="stretch"):
                st.session_state.pendiente = e
                st.rerun()

    for n, m in enumerate(st.session_state.mensajes):
        with st.chat_message("user" if m["rol"] == "user" else "assistant",
                             avatar="🧑" if m["rol"] == "user" else "🧠"):
            st.markdown(m["texto"])
            if m["rol"] == "assistant":
                mostrar_fuentes(m.get("fuentes", []), m.get("pregunta", ""), n)

    pregunta = st.chat_input("Escribe tu pregunta…") or st.session_state.pop("pendiente", None)
    if pregunta:
        historial = list(st.session_state.mensajes)
        st.session_state.mensajes.append({"rol": "user", "texto": pregunta})
        with st.chat_message("user", avatar="🧑"):
            st.markdown(pregunta)

        fuentes = cerebro.buscar(pregunta)
        if len(fuentes) < 3 and historial:  # pregunta de seguimiento: usa el contexto anterior
            previa = next((m["texto"] for m in reversed(historial) if m["rol"] == "user"), "")
            fuentes = cerebro.buscar(previa + " " + pregunta)

        with st.chat_message("assistant", avatar="🧠"):
            if limite_alcanzado():
                texto = respuesta_sin_clave(fuentes, f"Llegaste al límite de {MAX_PREGUNTAS_DEMO} respuestas de esta demo. "
                                                     "Te muestro los documentos relacionados. ¿Quieres Ontara Cerebro "
                                                     "para tu empresa? Escríbenos a C&M Labs.")
                st.markdown(texto)
            elif clave_activa() and fuentes:
                try:
                    texto = st.write_stream(preguntar_a_claude(pregunta, fuentes, historial))
                    st.session_state.preguntas += 1
                except Exception as ex:  # clave inválida, sin saldo o sin internet
                    nombre = type(ex).__name__
                    aviso = {"AuthenticationError": "La clave de API no es válida.",
                             "PermissionDeniedError": "La clave no tiene permiso. Revisa la cuenta en platform.claude.com.",
                             "RateLimitError": "Se alcanzó el límite de uso por ahora. Espera un momento e intenta de nuevo.",
                             "APIConnectionError": "No hay conexión a internet o el servicio no responde.",
                             "BadRequestError": "La solicitud fue rechazada (revisa que la cuenta de la API tenga saldo)."}
                    texto = "⚠️ " + aviso.get(nombre, f"Ocurrió un error: {ex}") + "\n\n" + respuesta_sin_clave(fuentes)
                    st.markdown(texto)
            else:
                texto = respuesta_sin_clave(fuentes)
                st.markdown(texto)
            n = len(st.session_state.mensajes)
            mostrar_fuentes(fuentes, pregunta, n)
        st.session_state.mensajes.append({"rol": "assistant", "texto": texto, "fuentes": fuentes,
                                          "pregunta": pregunta})

from paneles import pestana_cargar, pestana_gestionar, pestana_panel  # noqa: E402

if tab_cargar is not None:
    with tab_cargar:
        pestana_cargar(cerebro, config, guardar_config)
    with tab_gestion:
        pestana_gestionar(cerebro, abrir, config)
with tab_panel:
    pestana_panel(cerebro, DEMO, DATOS)


if DEMO:
    st.markdown('<div class="pie">Ontara Cerebro · un producto de C&M Labs · Palmira, Valle del Cauca</div>',
                unsafe_allow_html=True)
