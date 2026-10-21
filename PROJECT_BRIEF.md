# LabLens AI — Project Brief

## Problema

Los historiales de laboratorio longitudinales suelen acumular décadas de datos con nombres de pruebas inconsistentes, rangos cambiantes, resultados cualitativos y errores de captura. El caso que inspiró este proyecto cubre 1989–2026 y contiene 62 parámetros numéricos y más de mil mediciones.

## Solución

**LabLens AI** convierte ese expediente en una capa de comparación y consulta. El objetivo no es diagnosticar: es ayudar a responder tres preguntas operativas:

1. ¿Esta prueba nueva corresponde a alguna prueba histórica, aunque el nombre cambie?
2. ¿Qué cambió numéricamente desde el último registro conocido?
3. ¿Qué datos requieren verificación humana antes de utilizarlos?

## Componentes de IA

### 1. Entity / name matching
La app normaliza texto, usa aliases y similitud de cadenas para mapear nombres heterogéneos a un nombre canónico. Cada match expone un score de confianza.

### 2. Retrieval NLP
Un índice TF‑IDF recupera los registros más relacionados con una pregunta. Esto permite mostrar evidencia antes de responder.

### 3. LLM opcional con grounding
Un modelo generativo puede resumir exclusivamente la evidencia recuperada. El prompt le prohíbe diagnosticar, sugerir tratamiento o inventar causas.

## Componentes deterministas

La comparación de valores, delta porcentual y clasificación contra el rango transcrito son reglas, no IA. El proyecto las presenta como tales.

## Human-in-the-loop

Un match de baja confianza, un rango no interpretable o una bandera de calidad se conserva y se manda a revisión. No hay auto-corrección silenciosa.

## Privacidad

La demo pública usa datos sintéticos. Los datos de una persona real no deben publicarse en GitHub ni en Streamlit Community Cloud.

## Métricas propuestas

- Exactitud de matching de nombres en un set etiquetado.
- % de pruebas con match automático vs. revisión humana.
- Precision@k de retrieval para preguntas de prueba.
- Tasa de respuestas del LLM que citan únicamente evidencia recuperada.
- Número de datos dudosos correctamente enviados a revisión.

## Límites

- No interpreta causalidad médica.
- No diagnostica.
- No sustituye rangos ni unidades con conocimiento externo.
- No compara valores si no hay confianza suficiente en el nombre o la unidad.
