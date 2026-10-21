# LabLens AI

Proyecto académico de IA / data para organizar historiales de laboratorio longitudinales sin convertir el sistema en una herramienta diagnóstica.

## Qué demuestra

- Normalización y **matching aproximado de nombres de pruebas** (`GLU` → `Glucosa`, `Hb` → `Hemoglobina`).
- Comparación entre un estudio nuevo y un baseline histórico.
- Separación entre **valor fuera de rango** y **problema de calidad de datos**.
- Retrieval NLP (TF‑IDF) para recuperar evidencia relevante.
- LLM opcional con grounding: el modelo recibe solo la evidencia recuperada.
- Human-in-the-loop: matches dudosos y datos raros se mandan a revisión.

## Privacidad

La app incluida usa un **dataset sintético**. No contiene resultados de una persona real. El caso de uso original inspiró la estructura del proyecto, pero la demo pública altera/crea valores expresamente para presentación académica.

## Ejecutar localmente

```bash
python -m venv .venv
# Windows
.venv\\Scripts\\activate
# macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt
streamlit run app.py
```

## CSV para comparar un estudio

Columnas:

```text
prueba,valor,unidad,rango
GLU,116,mg/dL,70 - 110
Creat,0.96,mg/dL,0.70 - 1.20
```

Hay un ejemplo en `data/sample_new_study.csv` y también se puede descargar desde la app.

## OpenAI opcional

La app funciona sin API. Si se activa la opción generativa en **Ask LabLens**, la clave se ingresa en la sesión de Streamlit y no debe guardarse en GitHub.

## Deploy en Streamlit Community Cloud

1. Crear un repositorio en GitHub y subir esta carpeta.
2. Entrar a Streamlit Community Cloud.
3. Seleccionar el repositorio.
4. Main file: `app.py`.
5. Deploy.

No se necesita ningún secret si se usa la respuesta local. Para una versión con API fija, usar `st.secrets`; nunca escribir una API key en el código.

## Archivos

- `app.py` — interfaz Streamlit.
- `labcore.py` — matching, rangos y comparación.
- `data/baseline_summary_demo.csv` — baseline sintético.
- `data/sample_new_study.csv` — estudio nuevo sintético con alias.
- `data/quality_flags_demo.csv` — banderas de calidad sintéticas.
- `PROJECT_BRIEF.md` — explicación académica.
- `PRESENTATION_SCRIPT.md` — guion corto para exponer.
