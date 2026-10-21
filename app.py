from pathlib import Path
import io
import re

import pandas as pd
import plotly.express as px
import streamlit as st

from labcore import compare_study, summarize_changes

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    SKLEARN_OK = True
except Exception:
    SKLEARN_OK = False

try:
    from openai import OpenAI
    OPENAI_OK = True
except Exception:
    OPENAI_OK = False

BASE = Path(__file__).resolve().parent
DATA = BASE

st.set_page_config(page_title="LabLens AI", page_icon="🔬", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
.block-container {padding-top: 1.2rem; max-width: 1240px;}
[data-testid="stSidebar"] {background:#10283d;}
[data-testid="stSidebar"] * {color:#f5f7f9;}
.hero {background:linear-gradient(135deg,#10283d 0%,#173d59 68%,#1d5669 100%);padding:30px 34px;border-radius:22px;color:white;margin-bottom:18px;box-shadow:0 8px 22px rgba(16,40,61,.12);}
.hero h1 {margin:0;font-size:2.55rem;letter-spacing:-.03em;}
.hero p {margin:.45rem 0 0;color:#dce6ec;font-size:1.08rem;max-width:860px;}
.badge {display:inline-block;padding:5px 10px;border-radius:999px;background:#d79b35;color:#10283d;font-weight:800;font-size:.78rem;margin-bottom:10px;}
.card {background:white;border:1px solid #dde5ea;border-radius:16px;padding:18px;box-shadow:0 4px 14px rgba(16,40,61,.05);}
.small-note {font-size:.88rem;color:#526574;}
.ai-pill {display:inline-block;background:#e8f2f4;color:#145164;padding:4px 9px;border-radius:999px;font-size:.78rem;font-weight:700;margin-right:5px;}
</style>
""", unsafe_allow_html=True)

@st.cache_data
def load_demo():
    return (
        pd.read_csv(DATA / "baseline_summary_demo.csv"),
        pd.read_csv(DATA / "quality_flags_demo.csv"),
        pd.read_csv(DATA / "qualitative_demo.csv"),
        pd.read_csv(DATA / "timeline_demo.csv"),
        pd.read_csv(DATA / "sample_new_study.csv"),
    )

baseline, quality, qualitative, timeline, sample_new = load_demo()


def corpus_rows():
    docs = []
    for _, r in baseline.iterrows():
        docs.append({"kind":"resultado", "title":r["parametro"], "text":f"{r['parametro']}. Periodo {r['periodo']}. Valor {r['ultimo_valor']}. Rango {r['rango_transcrito']}. Estado {r['comparacion']}. Sección {r['seccion']}."})
    for _, r in quality.iterrows():
        docs.append({"kind":"calidad", "title":f"{r['tipo']} · {r['parametro']}", "text":f"Control de calidad. {r['tipo']}. Periodo {r['periodo']}. Parámetro {r['parametro']}. Dato {r['dato']}. Motivo {r['motivo']}"})
    for _, r in qualitative.iterrows():
        docs.append({"kind":"cualitativo", "title":r["parametro"], "text":f"Resultado cualitativo. {r['parametro']}. Periodo {r['periodo']}. Resultado {r['resultado']}. Laboratorio {r['laboratorio']}."})
    for _, r in timeline.iterrows():
        docs.append({"kind":"timeline", "title":f"{r['periodo']} · {r['fuente']}", "text":f"Nota histórica. Periodo {r['periodo']}. Fuente {r['fuente']}. {r['nota_original']}"})
    return docs

CORPUS = corpus_rows()

@st.cache_resource
def build_retriever(texts):
    if not SKLEARN_OK:
        return None, None
    vec = TfidfVectorizer(strip_accents="unicode", ngram_range=(1,2))
    mat = vec.fit_transform(texts)
    return vec, mat

VECTORIZER, MATRIX = build_retriever([d["text"] for d in CORPUS])


def retrieve(query, k=7):
    if SKLEARN_OK and VECTORIZER is not None:
        q = VECTORIZER.transform([query])
        scores = cosine_similarity(q, MATRIX).ravel()
        idx = scores.argsort()[::-1][:k]
        return [(CORPUS[i], float(scores[i])) for i in idx if scores[i] > 0.02]
    terms = [x for x in re.findall(r"\w+", query.lower()) if len(x) > 2]
    scored = []
    for d in CORPUS:
        score = sum(d["text"].lower().count(t) for t in terms)
        if score:
            scored.append((d, float(score)))
    return sorted(scored, key=lambda x:x[1], reverse=True)[:k]


def local_answer(query, hits):
    q = query.lower()
    if "fuera" in q or "rango" in q or "alter" in q:
        out = baseline[baseline.comparacion == "Fuera"]
        return f"En el dataset de demostración hay {len(out)} parámetros marcados como fuera del rango transcrito: " + ", ".join(out.parametro.tolist()) + ". La etiqueta describe una comparación matemática, no un diagnóstico."
    if any(w in q for w in ["error","captura","calidad","anomal"]):
        return f"Hay {len(quality)} banderas de calidad en la demo. LabLens las separa de los hallazgos de rango para evitar tratar un dato dudoso como si fuera una señal clínica confirmada."
    if hits:
        return "Encontré evidencia relacionada:\n\n" + "\n\n".join(f"• {d['text']}" for d,_ in hits[:4]) + "\n\nLabLens organiza evidencia; no infiere diagnósticos ni causas."
    return "No encontré evidencia suficiente en los datos cargados. Prueba con el nombre de una prueba, una fecha o una pregunta de calidad de datos."


def llm_answer(query, hits, api_key):
    context = "\n".join(f"- {d['text']}" for d,_ in hits[:8])
    client = OpenAI(api_key=api_key)
    resp = client.responses.create(
        model="gpt-5-mini",
        input=[
            {"role":"system","content":"Eres LabLens AI. Resume exclusivamente la evidencia suministrada. No diagnostiques, no sugieras tratamientos, no infieras causas. Distingue hallazgos de rango de problemas de calidad de datos. Si falta evidencia, dilo. Termina con 'Esto no sustituye la interpretación médica.'"},
            {"role":"user","content":f"Pregunta: {query}\n\nEvidencia:\n{context}"},
        ],
    )
    return resp.output_text


def download_csv(df, filename, label):
    st.download_button(label, df.to_csv(index=False).encode("utf-8-sig"), file_name=filename, mime="text/csv")

st.markdown('''<div class="hero"><span class="badge">PROYECTO ACADÉMICO · DATA + AI</span><h1>LabLens AI</h1><p>De resultados dispersos a evidencia navegable: normaliza nombres, compara estudios, detecta problemas de calidad y responde preguntas con trazabilidad.</p></div>''', unsafe_allow_html=True)

with st.sidebar:
    st.markdown("## 🔬 LabLens AI")
    st.caption("Demo pública con datos sintéticos. Ningún valor visible corresponde a una persona real.")
    page = st.radio("Navegación", ["Home", "Comparar estudio", "Signal vs. Noise", "Explorar expediente", "Ask LabLens", "Arquitectura IA", "Demo para clase"])
    st.markdown("---")
    st.markdown('<span class="ai-pill">NLP</span><span class="ai-pill">Matching</span><span class="ai-pill">RAG</span>', unsafe_allow_html=True)
    st.caption("LabLens no diagnostica ni sustituye la interpretación médica.")

if page == "Home":
    c1,c2,c3,c4 = st.columns(4)
    c1.metric("Pruebas en demo", len(baseline))
    c2.metric("Banderas de calidad", len(quality))
    c3.metric("Registros cualitativos", len(qualitative))
    c4.metric("Cobertura del caso real", "1989–2026")

    st.subheader("El problema")
    st.write("Un expediente largo acumula nombres inconsistentes, rangos que cambian, resultados cualitativos y posibles errores de captura. LabLens convierte ese material en una capa de consulta y comparación sin borrar la incertidumbre.")

    st.subheader("Qué hace la IA aquí")
    a,b,c = st.columns(3)
    with a:
        st.markdown("### 1 · Matching inteligente")
        st.write("Reconoce que **GLU**, *glucose* y *glucosa sanguínea* probablemente se refieren a la misma prueba, y muestra la confianza del match.")
    with b:
        st.markdown("### 2 · Retrieval con evidencia")
        st.write("Busca los fragmentos del expediente más relacionados con la pregunta antes de generar una respuesta.")
    with c:
        st.markdown("### 3 · Human-in-the-loop")
        st.write("Los valores dudosos no se 'arreglan'. Se marcan para verificación contra el informe original.")

    st.subheader("Snapshot del expediente de demostración")
    display = baseline[["parametro","periodo","ultimo_valor","rango_transcrito","comparacion","seccion"]]
    st.dataframe(display, use_container_width=True, hide_index=True)

elif page == "Comparar estudio":
    st.subheader("Comparar un estudio nuevo")
    st.write("Sube un CSV de laboratorio o usa el archivo de demo. LabLens normaliza los nombres de pruebas, enlaza contra el último registro conocido y calcula qué cambió.")

    col_a,col_b = st.columns([1,1])
    with col_a:
        uploaded = st.file_uploader("CSV nuevo", type=["csv"], help="Columnas esperadas: prueba, valor, unidad, rango")
    with col_b:
        use_demo = st.toggle("Usar estudio nuevo de demostración", value=uploaded is None)

    if uploaded is not None:
        try:
            new_study = pd.read_csv(uploaded)
        except Exception as e:
            st.error(f"No pude leer el CSV: {e}")
            st.stop()
    elif use_demo:
        new_study = sample_new.copy()
    else:
        new_study = None

    st.caption("Formato requerido: `prueba, valor, unidad, rango`. El archivo incluido usa alias como GLU, Creat, LDL colesterol y Hb para demostrar el matching.")
    download_csv(sample_new, "sample_new_study.csv", "Descargar CSV de ejemplo")

    if new_study is not None:
        required = {"prueba","valor","rango"}
        missing = required - set(new_study.columns)
        if missing:
            st.error("Faltan columnas: " + ", ".join(sorted(missing)))
        else:
            if "unidad" not in new_study.columns:
                new_study["unidad"] = ""
            compared = compare_study(new_study, baseline)
            summary = summarize_changes(compared)
            m1,m2,m3,m4 = st.columns(4)
            m1.metric("Matches", summary["matched"])
            m2.metric("Sin match", summary["unmatched"])
            m3.metric("Fuera de rango", summary["outside"])
            low_conf = int(((compared.confianza_match < .78) & (compared.parametro != "Sin match")).sum())
            m4.metric("Matches a confirmar", low_conf)

            st.markdown("### Resultado del matching")
            st.dataframe(compared, use_container_width=True, hide_index=True)
            download_csv(compared, "lablens_comparison.csv", "Descargar comparación")

            if not summary["largest_changes"].empty:
                st.markdown("### Qué cambió más")
                ch = summary["largest_changes"].copy()
                fig = px.bar(ch.sort_values("abs_delta_pct"), x="abs_delta_pct", y="parametro", orientation="h", text="delta_pct", labels={"abs_delta_pct":"Cambio absoluto (%)","parametro":""})
                fig.update_traces(texttemplate="%{text}%", textposition="outside")
                fig.update_layout(height=350, showlegend=False)
                st.plotly_chart(fig, use_container_width=True)
                st.caption("El porcentaje solo describe el cambio numérico entre dos registros. No mide gravedad clínica.")

            review = compared[compared.revision_datos != "OK"]
            if not review.empty:
                st.warning("Hay filas que necesitan revisión humana antes de cualquier uso posterior.")
                st.dataframe(review[["prueba_original","parametro","confianza_match","estado_nuevo","revision_datos"]], use_container_width=True, hide_index=True)

elif page == "Signal vs. Noise":
    st.subheader("Signal vs. Noise")
    st.write("LabLens separa dos conceptos que suelen mezclarse: **un valor fuera de un rango transcrito** y **un dato que quizá no es confiable o comparable**.")
    left,right = st.columns(2)
    with left:
        st.markdown("### 📌 Señal matemática")
        outside = baseline[baseline.comparacion == "Fuera"]
        st.dataframe(outside[["parametro","ultimo_valor","rango_transcrito","periodo"]], use_container_width=True, hide_index=True)
    with right:
        st.markdown("### 🧹 Ruido / calidad de datos")
        st.dataframe(quality[["tipo","periodo","parametro","dato"]], use_container_width=True, hide_index=True)
    st.info("Diseño deliberado: LabLens nunca corrige silenciosamente un dato dudoso. Conserva el valor, explica la bandera y pide verificación.")

elif page == "Explorar expediente":
    st.subheader("Explorar expediente")
    section = st.selectbox("Sección", ["Todas"] + sorted(baseline.seccion.unique().tolist()))
    state = st.multiselect("Estado", ["Dentro","Fuera","Sin rango"], default=["Dentro","Fuera"])
    view = baseline.copy()
    if section != "Todas":
        view = view[view.seccion == section]
    if state:
        view = view[view.comparacion.isin(state)]
    st.dataframe(view, use_container_width=True, hide_index=True)

    st.markdown("### Línea del tiempo documental")
    for _,r in timeline.iloc[::-1].iterrows():
        with st.expander(f"{r.periodo} · {r.fuente}"):
            st.write(r.nota_original)
    st.markdown("### Resultados cualitativos")
    st.dataframe(qualitative, use_container_width=True, hide_index=True)

elif page == "Ask LabLens":
    st.subheader("Ask LabLens")
    st.write("Pregunta sobre el expediente. Primero se recupera evidencia relevante; después se responde usando solo esa evidencia.")
    query = st.text_input("Pregunta", placeholder="Ej. ¿Qué datos tienen banderas de calidad?")
    use_llm = st.toggle("Usar modelo generativo (opcional)", value=False)
    api_key = ""
    if use_llm:
        api_key = st.text_input("OpenAI API key", type="password", help="Solo se usa durante esta sesión. No la guardes en GitHub.")
    if st.button("Analizar", type="primary", disabled=not bool(query)):
        hits = retrieve(query)
        with st.expander("Evidencia recuperada", expanded=True):
            if hits:
                for d,s in hits:
                    st.markdown(f"**{d['title']}** · relevancia {s:.2f}")
                    st.caption(d["text"])
            else:
                st.write("Sin coincidencias relevantes.")
        try:
            answer = llm_answer(query, hits, api_key) if use_llm and api_key and OPENAI_OK else local_answer(query, hits)
        except Exception as e:
            st.warning(f"El modelo generativo no respondió ({e}). Muestro la respuesta local con evidencia.")
            answer = local_answer(query, hits)
        st.markdown("### Respuesta")
        st.write(answer)

elif page == "Arquitectura IA":
    st.subheader("Arquitectura IA")
    st.code("""NUEVO LAB / HISTÓRICO\n        │\n        ▼\n  Normalización de nombres\n        │\n        ├──► matching + score de confianza\n        │\n        ▼\n Comparación contra baseline\n        │\n        ├──► rango transcrito\n        ├──► delta numérico\n        └──► bandera de revisión\n        │\n        ▼\n  Retrieval NLP (TF-IDF)\n        │\n        ▼\n LLM opcional con grounding\n        │\n        ▼\n Respuesta + evidencia + límites""", language="text")

    st.markdown("### Decisiones de diseño")
    st.markdown("""
- **Privacidad:** la demo pública usa valores sintéticos.
- **Trazabilidad:** el usuario puede ver exactamente qué evidencia se recuperó.
- **No diagnóstico:** *Fuera de rango* es una etiqueta matemática, no una conclusión clínica.
- **No auto-corrección:** los valores raros quedan visibles y se mandan a revisión humana.
- **Confianza visible:** un match aproximado de nombres no se presenta como certeza.
""")

    st.markdown("### Qué es IA y qué no")
    st.write("El matching de nombres y la recuperación de evidencia son componentes algorítmicos/NLP. El LLM es opcional y se usa solo para explicación. El cálculo de delta y la comparación contra rangos son reglas deterministas; etiquetarlas como 'IA' sería engañoso.")

elif page == "Demo para clase":
    st.subheader("Demo de 3 minutos")
    st.markdown("""
**0:00–0:30 — El problema**  
“Tenemos décadas de laboratorios, diferentes nombres, métodos y rangos. Encontrar qué cambió y qué dato es dudoso toma tiempo.”

**0:30–1:20 — Matching inteligente**  
Entra a **Comparar estudio** y usa la demo. Enseña que *GLU → Glucosa*, *Creat → Creatinina* y *Hb → Hemoglobina*. Señala el **score de confianza** y el registro sin match.

**1:20–2:00 — Qué cambió**  
Muestra la gráfica de cambios y la diferencia entre *fuera de rango* y *revisar datos*. Aclara que el sistema no diagnostica.

**2:00–2:40 — Ask LabLens**  
Pregunta: “¿Qué datos tienen banderas de calidad?” Abre **Evidencia recuperada** para demostrar grounding y trazabilidad.

**2:40–3:00 — Cierre**  
“LabLens no reemplaza al médico. Resuelve el problema previo: ordenar, homologar y encontrar evidencia confiable en un expediente longitudinal.”
""")
    st.success("Frase de cierre: **La IA no decide qué significa un resultado; ayuda a encontrar qué merece ser revisado y por qué.**")

st.markdown("---")
st.caption("LabLens AI · prototipo educativo con dataset público sintético. No diagnostica ni sustituye a profesionales de salud.")
