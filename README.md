# 🧠 Ontara Cerebro · C&M Labs

**Pregúntale a todos los documentos de una empresa y recibe respuestas con la fuente exacta.**

Ontara Cerebro lee documentos PDF, Word, PowerPoint, Excel, CSV y Markdown, y los organiza en un índice de búsqueda. Cuando haces una pregunta, busca los fragmentos más relevantes y Claude redacta la respuesta citando de qué archivo salió cada dato.

Esta es la **demo pública**. Usa los documentos de *Comercializadora El Samán S.A.S.*, una empresa ficticia creada por C&M Labs (carpeta `demo_docs/`). Todos sus datos son inventados.

## Cómo funciona
1. **Lectura:** `motor.py` extrae el texto de cada documento y lo divide en fragmentos.
2. **Índice:** los fragmentos se guardan en SQLite FTS5, con búsqueda por relevancia BM25 que no distingue tildes ni mayúsculas.
3. **Respuesta:** `app.py`, hecho en Streamlit, envía a Claude solo los fragmentos relevantes y muestra la respuesta con sus fuentes.

## Publicarla en Streamlit Community Cloud
1. En share.streamlit.io, crea una app a partir de este repositorio, con el archivo principal `app.py`.
2. En **Settings → Secrets** agrega la clave de API:
   ```toml
   ANTHROPIC_API_KEY = "sk-ant-..."
   ```
3. Sin clave, la demo funciona en modo búsqueda. Con clave, cada visitante tiene un límite de 15 respuestas.

## Ejecutarla en tu computador
```bash
pip install -r requirements.txt
streamlit run app.py
```

---
Un producto de **C&M Labs** · Palmira, Valle del Cauca, Colombia.
