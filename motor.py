"""Ontara Cerebro · motor de indexación y búsqueda (C&M Labs).

Lee documentos de las carpetas configuradas, los divide en fragmentos y los
guarda en un índice SQLite FTS5 (búsqueda por relevancia BM25, sin tildes).
Todo queda en el equipo del usuario.
"""
import os
import re
import sqlite3
import unicodedata
import zipfile
from html import unescape

EXTENSIONES = (".pdf", ".docx", ".pptx", ".xlsx", ".xlsm", ".txt", ".csv", ".md", ".html", ".htm")
CARPETAS_IGNORADAS = {"00_Ontara_Cerebro", "13_Telegram_Unigram", "node_modules", ".git",
                      "__pycache__", "AppData", "_files", "Ontara_Cerebro"}
PALABRAS_POR_FRAGMENTO = 350
SOLAPE = 60

STOPWORDS = set("""
a al algo algun alguna algunas alguno algunos ante antes aqui asi aun cada como con contra cual cuales
cuando cuanto de del desde donde dos el ella ellas ello ellos en entre era eran es esa esas ese eso esos
esta estaba estado estan estar estas este esto estos fue fueron ha habia han hasta hay la las le les lo
los mas me mi mis mucho muy nada ni no nos nosotros o os otra otro para pero poco por porque que quien
quienes se sea segun ser si sido sin sobre solo son su sus tambien tan tanto te tengo tiene tienen todo
todos tu tus un una uno unos usted ustedes y ya yo dime dame cual cuales hay sabes sobre puedes podrias
necesito quiero saber cuentame explicame resume resumen informacion archivo archivos documento documentos
dice dicen hablan habla tema temas the of and to in is for on with what which
""".split())


def normalizar(texto):
    texto = unicodedata.normalize("NFKD", texto.lower())
    return "".join(c for c in texto if not unicodedata.combining(c))


# ---------------------------------------------------------------- extracción
def _pdf(ruta):
    from pypdf import PdfReader
    lector = PdfReader(ruta)
    partes = []
    for i, pagina in enumerate(lector.pages[:150], 1):
        try:
            t = pagina.extract_text() or ""
        except Exception:
            t = ""
        if t.strip():
            partes.append(f"[Página {i}]\n{t}")
    return "\n".join(partes)


def _docx(ruta):
    import docx
    d = docx.Document(ruta)
    partes = [p.text for p in d.paragraphs if p.text.strip()]
    for tabla in d.tables:
        for fila in tabla.rows:
            partes.append(" | ".join(c.text.strip() for c in fila.cells))
    return "\n".join(partes)


def _pptx(ruta):
    import pptx
    partes = []
    for i, diapositiva in enumerate(pptx.Presentation(ruta).slides, 1):
        partes.append(f"[Diapositiva {i}]")
        for forma in diapositiva.shapes:
            if getattr(forma, "has_text_frame", False) and forma.text_frame.text.strip():
                partes.append(forma.text_frame.text)
        if diapositiva.has_notes_slide:
            notas = diapositiva.notes_slide.notes_text_frame.text
            if notas.strip():
                partes.append("Notas: " + notas)
    return "\n".join(partes)


def _xlsx(ruta):
    import openpyxl
    libro = openpyxl.load_workbook(ruta, read_only=True, data_only=True)
    partes = []
    for hoja in libro.worksheets:
        partes.append(f"[Hoja: {hoja.title}]")
        for n, fila in enumerate(hoja.iter_rows(values_only=True)):
            if n >= 500:
                partes.append("...(hoja recortada)")
                break
            valores = ["" if v is None else str(v) for v in fila]
            if any(valores):
                partes.append(" | ".join(valores).strip(" |"))
    libro.close()
    return "\n".join(partes)


def _texto_plano(ruta):
    with open(ruta, "rb") as f:
        datos = f.read(2_000_000)
    for codificacion in ("utf-8", "latin-1"):
        try:
            return datos.decode(codificacion)
        except UnicodeDecodeError:
            continue
    return datos.decode("utf-8", "ignore")


def _html(ruta):
    t = _texto_plano(ruta)
    t = re.sub(r"(?is)<(script|style).*?</\1>", " ", t)
    t = re.sub(r"<[^>]+>", " ", t)
    return unescape(re.sub(r"\s+", " ", t))


def extraer_texto(ruta, carpeta_ocr=None, raiz=None):
    ext = os.path.splitext(ruta)[1].lower()
    funciones = {".pdf": _pdf, ".docx": _docx, ".pptx": _pptx, ".xlsx": _xlsx, ".xlsm": _xlsx,
                 ".html": _html, ".htm": _html}
    texto = funciones.get(ext, _texto_plano)(ruta)
    # PDF escaneado: usa el texto OCR ya generado, si existe
    if ext == ".pdf" and len(texto.split()) < 20 and carpeta_ocr and raiz:
        alterno = os.path.join(carpeta_ocr, os.path.relpath(ruta, raiz) + ".txt")
        if os.path.exists(alterno):
            texto = _texto_plano(alterno)
    return texto


def fragmentar(texto):
    palabras = texto.split()
    if not palabras:
        return []
    paso = PALABRAS_POR_FRAGMENTO - SOLAPE
    return [" ".join(palabras[i:i + PALABRAS_POR_FRAGMENTO])
            for i in range(0, max(len(palabras) - SOLAPE, 1), paso)]


# ---------------------------------------------------------------- índice
class Cerebro:
    def __init__(self, ruta_bd):
        os.makedirs(os.path.dirname(ruta_bd), exist_ok=True)
        self.bd = sqlite3.connect(ruta_bd, check_same_thread=False)
        self.bd.executescript("""
            CREATE TABLE IF NOT EXISTS documentos(
                ruta TEXT PRIMARY KEY, raiz TEXT, nombre TEXT, carpeta TEXT,
                mtime REAL, tamano INTEGER, palabras INTEGER, error TEXT);
            CREATE VIRTUAL TABLE IF NOT EXISTS fragmentos USING fts5(
                ruta UNINDEXED, nombre, texto, orden UNINDEXED,
                tokenize = "unicode61 remove_diacritics 2");
        """)

    # -- inventario
    @staticmethod
    def listar_archivos(raices):
        for raiz in raices:
            for actual, carpetas, archivos in os.walk(raiz):
                carpetas[:] = [c for c in carpetas if c not in CARPETAS_IGNORADAS
                               and not c.startswith(".") and not c.endswith("_files")]
                for nombre in archivos:
                    if nombre.lower().endswith(EXTENSIONES) and not nombre.startswith(("~$", ".", "_registro_de_movimientos")):
                        yield raiz, os.path.join(actual, nombre)

    def actualizar(self, raices, carpeta_ocr=None, progreso=None):
        """Indexa archivos nuevos o modificados y borra los que ya no existen."""
        archivos = list(self.listar_archivos(raices))
        conocidos = {r: (m, t) for r, m, t in self.bd.execute(
            "SELECT ruta, mtime, tamano FROM documentos")}
        vistos, nuevos, errores = set(), 0, 0
        for i, (raiz, ruta) in enumerate(archivos, 1):
            vistos.add(ruta)
            try:
                st = os.stat(ruta)
            except OSError:
                continue
            if conocidos.get(ruta) == (st.st_mtime, st.st_size):
                continue
            if progreso:
                progreso(i / len(archivos), os.path.basename(ruta))
            error = None
            try:
                texto = extraer_texto(ruta, carpeta_ocr, raiz)
            except Exception as ex:  # archivo dañado o protegido
                texto, error = "", str(ex)[:200]
                errores += 1
            nombre = os.path.basename(ruta)
            carpeta = os.path.relpath(os.path.dirname(ruta), raiz)
            self.bd.execute("DELETE FROM fragmentos WHERE ruta = ?", (ruta,))
            for orden, frag in enumerate(fragmentar(texto)):
                self.bd.execute("INSERT INTO fragmentos VALUES (?,?,?,?)",
                                (ruta, nombre, frag, orden))
            self.bd.execute("INSERT OR REPLACE INTO documentos VALUES (?,?,?,?,?,?,?,?)",
                            (ruta, raiz, nombre, carpeta, st.st_mtime, st.st_size,
                             len(texto.split()), error))
            nuevos += 1
            if nuevos % 25 == 0:
                self.bd.commit()
        borrados = [r for r in conocidos if r not in vistos]
        for r in borrados:
            self.bd.execute("DELETE FROM fragmentos WHERE ruta = ?", (r,))
            self.bd.execute("DELETE FROM documentos WHERE ruta = ?", (r,))
        self.bd.commit()
        return {"revisados": len(archivos), "nuevos": nuevos, "borrados": len(borrados),
                "errores": errores}

    def estadisticas(self):
        docs, palabras = self.bd.execute(
            "SELECT COUNT(*), COALESCE(SUM(palabras),0) FROM documentos").fetchone()
        legibles = self.bd.execute(
            "SELECT COUNT(*) FROM documentos WHERE palabras >= 20").fetchone()[0]
        carpetas = self.bd.execute("""
            SELECT CASE WHEN instr(carpeta, '/') > 0 THEN substr(carpeta, 1, instr(carpeta, '/') - 1)
                        WHEN instr(carpeta, '\\') > 0 THEN substr(carpeta, 1, instr(carpeta, '\\') - 1)
                        ELSE carpeta END AS area, COUNT(*)
            FROM documentos GROUP BY area ORDER BY 2 DESC""").fetchall()
        return {"documentos": docs, "palabras": palabras, "legibles": legibles, "areas": carpetas}

    # -- búsqueda
    @staticmethod
    def consulta_fts(pregunta):
        palabras = re.findall(r"[a-z0-9ñ]+", normalizar(pregunta))
        terminos = []
        for p in palabras:
            if p in STOPWORDS or len(p) < 3:
                continue
            # raíz simple para tolerar plurales y conjugaciones
            raiz = p[:6] if len(p) > 7 else p
            terminos.append(f'"{raiz}"*' if len(p) >= 5 else f'"{p}"')
        terminos = list(dict.fromkeys(terminos))
        return " OR ".join(terminos)

    def buscar(self, pregunta, limite=8, por_documento=2):
        consulta = self.consulta_fts(pregunta)
        if not consulta:
            return []
        filas = self.bd.execute("""
            SELECT f.ruta, f.nombre, f.texto, f.orden, bm25(fragmentos, 0, 4.0, 1.0) AS puntaje,
                   d.carpeta
            FROM fragmentos f JOIN documentos d ON d.ruta = f.ruta
            WHERE fragmentos MATCH ? ORDER BY puntaje LIMIT 120""", (consulta,)).fetchall()
        resultados, conteo = [], {}
        for ruta, nombre, texto, orden, puntaje, carpeta in filas:
            if conteo.get(ruta, 0) >= por_documento:
                continue
            conteo[ruta] = conteo.get(ruta, 0) + 1
            resultados.append({"ruta": ruta, "nombre": nombre, "carpeta": carpeta,
                               "texto": texto, "orden": orden, "puntaje": -puntaje})
            if len(resultados) >= limite:
                break
        return resultados

    @staticmethod
    def resaltar(texto, pregunta, largo=420):
        """Devuelve un extracto centrado en el primer término encontrado."""
        claves = [p for p in re.findall(r"[a-z0-9ñ]+", normalizar(pregunta))
                  if p not in STOPWORDS and len(p) >= 3]
        base = normalizar(texto)
        pos = min([base.find(c[:6]) for c in claves if base.find(c[:6]) >= 0] or [0])
        inicio = max(0, pos - largo // 3)
        extracto = texto[inicio:inicio + largo]
        return ("…" if inicio else "") + extracto + ("…" if inicio + largo < len(texto) else "")
