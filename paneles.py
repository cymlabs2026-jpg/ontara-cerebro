"""Ontara Cerebro · pestañas Cargar, Gestionar y Panel (C&M Labs)."""
import datetime
import json
import os
import re
import unicodedata

import pandas as pd
import streamlit as st

INICIO = os.path.expanduser("~")
DOCUMENTOS = os.path.join(INICIO, "Documents")
CARGAS = os.path.join(DOCUMENTOS if os.path.isdir(DOCUMENTOS) else INICIO, "Ontara_Cargas")
PANEL_DIR = os.path.join(DOCUMENTOS if os.path.isdir(DOCUMENTOS) else INICIO, "Ontara_Cerebro_Panel")
AREAS = ["UPB", "C&M Labs", "Emaús", "Sazón al Barril", "Finanzas y canal", "Personal", "Otros"]
TIPOS_SUBIDA = ["pdf", "docx", "pptx", "xlsx", "xlsm", "txt", "csv", "md", "html"]
ACENTO = "#22D3EE"


def asegurar_cargas(config, guardar_config):
    """Crea la carpeta de cargas y la agrega a las carpetas que lee el cerebro."""
    os.makedirs(CARGAS, exist_ok=True)
    if CARGAS not in config["carpetas"]:
        config["carpetas"].append(CARGAS)
        guardar_config(config)


def _slug(texto, largo=60):
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    texto = re.sub(r"[^A-Za-z0-9]+", "_", texto).strip("_")
    return texto[:largo] or "nota"


def _ruta_libre(carpeta, nombre):
    base, ext = os.path.splitext(nombre)
    ruta, n = os.path.join(carpeta, nombre), 2
    while os.path.exists(ruta):
        ruta = os.path.join(carpeta, f"{base} ({n}){ext}")
        n += 1
    return ruta


def _raiz_de(ruta, carpetas):
    candidatas = [c for c in carpetas if os.path.abspath(ruta).startswith(os.path.abspath(c) + os.sep)]
    return max(candidatas, key=len) if candidatas else os.path.dirname(ruta)


# ---------------------------------------------------------------- Cargar
def pestana_cargar(cerebro, config, guardar_config):
    asegurar_cargas(config, guardar_config)
    st.markdown("#### 📥 Subir documentos")
    st.caption(f"Se guardan en `{CARGAS}` dentro de la carpeta del área que elijas, y el cerebro los lee al instante.")
    c1, c2 = st.columns([1, 2])
    area = c1.selectbox("Área", AREAS, key="area_subida")
    if "subida_n" not in st.session_state:
        st.session_state.subida_n = 0
    archivos = c2.file_uploader("Arrastra aquí tus archivos", type=TIPOS_SUBIDA, accept_multiple_files=True,
                                key=f"subida_{st.session_state.subida_n}")
    if archivos and st.button(f"Guardar y leer {len(archivos)} archivo(s)", type="primary"):
        destino = os.path.join(CARGAS, area)
        os.makedirs(destino, exist_ok=True)
        leidos, fallidos = [], []
        for a in archivos:
            ruta = _ruta_libre(destino, a.name)
            with open(ruta, "wb") as f:
                f.write(a.getbuffer())
            (leidos if cerebro.indexar_archivo(CARGAS, ruta) else fallidos).append(os.path.basename(ruta))
        st.session_state.subida_n += 1
        st.session_state.aviso_carga = (leidos, fallidos)
        st.rerun()
    if "aviso_carga" in st.session_state:
        leidos, fallidos = st.session_state.pop("aviso_carga")
        if leidos:
            st.success("Listos para preguntar: " + ", ".join(leidos))
        if fallidos:
            st.warning("Se guardaron pero no se pudo leer su texto: " + ", ".join(fallidos))

    st.divider()
    st.markdown("#### 📝 Nota rápida")
    st.caption("Escribe una idea, un acuerdo o un apunte. Queda guardado como archivo y el cerebro lo lee de una vez.")
    with st.form("nota_rapida", clear_on_submit=True):
        c1, c2 = st.columns([2, 1])
        titulo = c1.text_input("Título")
        area_nota = c2.selectbox("Área", AREAS, key="area_nota")
        cuerpo = st.text_area("Contenido", height=160)
        if st.form_submit_button("Guardar nota", type="primary"):
            if not titulo.strip() or not cuerpo.strip():
                st.warning("La nota necesita título y contenido.")
            else:
                hoy = datetime.date.today().isoformat()
                destino = os.path.join(CARGAS, area_nota)
                os.makedirs(destino, exist_ok=True)
                ruta = _ruta_libre(destino, f"{hoy}_{_slug(titulo)}.md")
                with open(ruta, "w", encoding="utf-8") as f:
                    f.write(f"# {titulo.strip()}\nÁrea: {area_nota} · Fecha: {hoy} · Origen: nota rápida en Ontara Cerebro\n\n{cuerpo.strip()}\n")
                cerebro.indexar_archivo(CARGAS, ruta)
                st.success(f"Nota guardada: {os.path.basename(ruta)}")

    recientes = [d for d in cerebro.documentos() if d["ruta"].startswith(CARGAS)][:10]
    if recientes:
        st.divider()
        st.markdown("#### Últimos cargados")
        for d in recientes:
            fecha = datetime.datetime.fromtimestamp(d["mtime"]).strftime("%d/%m/%Y %H:%M")
            st.markdown(f"- **{d['nombre']}** · {d['area']} · {fecha}")


# ---------------------------------------------------------------- Gestionar
def pestana_gestionar(cerebro, abrir, config):
    docs = cerebro.documentos()
    st.markdown("#### 🗂️ Documentos del cerebro")
    c1, c2, c3 = st.columns([2, 2, 1])
    texto = c1.text_input("Buscar por nombre", placeholder="Ej: parcial, cartera, emaús…")
    areas = sorted({d["area"] for d in docs})
    filtro_areas = c2.multiselect("Áreas", areas, placeholder="Todas")
    solo_ilegibles = c3.checkbox("Solo no legibles")
    def coincide(d):
        if texto and texto.lower() not in d["nombre"].lower():
            return False
        if filtro_areas and d["area"] not in filtro_areas:
            return False
        return not solo_ilegibles or not d["legible"]
    vista = [d for d in docs if coincide(d)]
    st.caption(f"{len(vista)} de {len(docs)} documentos")
    if vista:
        tabla = pd.DataFrame([{"Documento": d["nombre"], "Área": d["area"], "Tipo": d["tipo"],
                               "Palabras": d["palabras"], "Legible": "Sí" if d["legible"] else "No",
                               "Modificado": datetime.datetime.fromtimestamp(d["mtime"]).strftime("%Y-%m-%d")}
                              for d in vista])
        st.dataframe(tabla, width="stretch", hide_index=True, height=320)

    etiquetas = {d["ruta"]: f"{d['nombre']} — {d['area']}" for d in vista}
    elegidos = st.multiselect("Selecciona documentos para actuar sobre ellos", list(etiquetas),
                              format_func=lambda r: etiquetas[r], placeholder="Elige uno o varios documentos")
    if elegidos:
        c1, c2, c3 = st.columns(3)
        if len(elegidos) == 1 and c1.button("📂 Abrir archivo", width="stretch"):
            abrir(elegidos[0])
        if c2.button(f"🚫 Quitar del cerebro ({len(elegidos)})", width="stretch",
                     help="El archivo sigue en tu PC; solo deja de usarse para responder."):
            cerebro.quitar(elegidos)
            st.session_state.aviso_gestion = f"{len(elegidos)} documento(s) quitados del cerebro. El archivo sigue en tu PC."
            st.rerun()
        with c3.popover(f"🗑️ Enviar a la papelera ({len(elegidos)})", width="stretch"):
            st.markdown("Los archivos irán a la **Papelera de reciclaje** de Windows; desde ahí puedes recuperarlos.")
            if st.checkbox(f"Confirmo enviar {len(elegidos)} archivo(s) a la papelera"):
                if st.button("Enviar a la papelera", type="primary"):
                    from send2trash import send2trash
                    enviados, errores = [], []
                    for r in elegidos:
                        try:
                            send2trash(r)
                            enviados.append(r)
                        except Exception as ex:  # archivo abierto o sin permiso
                            errores.append(f"{os.path.basename(r)} ({ex})")
                    cerebro.olvidar(enviados)
                    st.session_state.aviso_gestion = (f"{len(enviados)} archivo(s) enviados a la papelera."
                                                      + (" No se pudo: " + "; ".join(errores) if errores else ""))
                    st.rerun()
    if "aviso_gestion" in st.session_state:
        st.success(st.session_state.pop("aviso_gestion"))

    quitados = cerebro.lista_excluidos()
    with st.expander(f"Documentos quitados del cerebro ({len(quitados)})"):
        if not quitados:
            st.caption("No has quitado ninguno.")
        else:
            volver = st.multiselect("Selecciona para volver a incluir", [r for r, _ in quitados],
                                    format_func=lambda r: os.path.basename(r), placeholder="Elige documentos")
            if volver and st.button("Volver a incluir"):
                cerebro.reincluir(volver)
                for r in volver:
                    if os.path.exists(r):
                        cerebro.indexar_archivo(_raiz_de(r, config["carpetas"]), r, config.get("carpeta_ocr"))
                st.rerun()


# ---------------------------------------------------------------- Panel
def _tabla_panel(docs):
    df = pd.DataFrame(docs)
    if df.empty:
        return df
    df["mes"] = pd.to_datetime(df["mtime"], unit="s").dt.strftime("%Y-%m")
    return df


def resumen(docs):
    df = _tabla_panel(docs)
    if df.empty:
        return {}
    por_area = df.groupby("area").agg(documentos=("ruta", "count"), palabras=("palabras", "sum"),
                                      legibles=("legible", "sum")).reset_index().sort_values("documentos", ascending=False)
    por_tipo = df.groupby("tipo").size().reset_index(name="documentos").sort_values("documentos", ascending=False)
    por_mes = df.groupby("mes").size().reset_index(name="documentos").sort_values("mes")
    return {
        "generado": datetime.datetime.now().isoformat(timespec="seconds"),
        "totales": {"documentos": int(len(df)), "palabras": int(df["palabras"].sum()),
                    "legibles": int(df["legible"].sum()), "areas": int(df["area"].nunique())},
        "por_area": por_area.astype({"legibles": int}).to_dict("records"),
        "por_tipo": por_tipo.to_dict("records"),
        "por_mes": por_mes.tail(18).to_dict("records"),
        "no_legibles": df[~df["legible"]][["nombre", "area", "tipo"]].to_dict("records"),
        "mas_extensos": df.nlargest(10, "palabras")[["nombre", "area", "palabras"]].to_dict("records"),
        "recientes": df.nlargest(15, "mtime")[["nombre", "area", "mes"]].to_dict("records"),
    }


def pestana_panel(cerebro, demo, datos_dir):
    docs = cerebro.documentos()
    if not docs:
        st.info("Todavía no hay documentos. Pulsa **Actualizar cerebro** en la barra lateral.")
        return
    r = resumen(docs)
    t = r["totales"]
    c = st.columns(4)
    c[0].metric("Documentos", f"{t['documentos']:,}")
    c[1].metric("Palabras", f"{t['palabras']:,}")
    c[2].metric("Se pueden leer", f"{t['legibles'] / t['documentos']:.0%}")
    c[3].metric("Áreas", t["areas"])

    area = pd.DataFrame(r["por_area"]).set_index("area")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**Documentos por área**")
        st.bar_chart(area["documentos"], color=ACENTO, horizontal=True, height=320)
    with c2:
        st.markdown("**Palabras por área** (cuánto conocimiento hay en cada una)")
        st.bar_chart(area["palabras"], color="#A78BFA", horizontal=True, height=320)
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**Documentos por mes** (fecha de última modificación)")
        st.bar_chart(pd.DataFrame(r["por_mes"]).set_index("mes")["documentos"], color=ACENTO, height=260)
    with c2:
        st.markdown("**Tipos de archivo**")
        st.bar_chart(pd.DataFrame(r["por_tipo"]).set_index("tipo")["documentos"], color="#F59E0B", height=260)

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**Los 10 más extensos**")
        st.dataframe(pd.DataFrame(r["mas_extensos"]).rename(columns={"nombre": "Documento", "area": "Área",
                                                                     "palabras": "Palabras"}),
                     hide_index=True, width="stretch")
    with c2:
        st.markdown(f"**No se pudieron leer** ({len(r['no_legibles'])})")
        if r["no_legibles"]:
            st.dataframe(pd.DataFrame(r["no_legibles"]).rename(columns={"nombre": "Documento", "area": "Área",
                                                                        "tipo": "Tipo"}),
                         hide_index=True, width="stretch")
            st.caption("Suelen ser PDF escaneados o protegidos. Puedes quitarlos en Gestionar.")
        else:
            st.caption("Todos los documentos se leyeron bien.")

    if not demo:
        os.makedirs(PANEL_DIR, exist_ok=True)
        with open(os.path.join(PANEL_DIR, "resumen_cerebro.json"), "w", encoding="utf-8") as f:
            json.dump(r, f, ensure_ascii=False, indent=2)
        st.caption(f"Resumen exportado para el tablero de Claude en `{PANEL_DIR}` (sin el contenido de tus documentos).")
