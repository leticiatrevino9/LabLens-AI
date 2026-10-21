# Guion de presentación — LabLens AI

## Pitch de 30 segundos

LabLens AI organiza historiales de laboratorio que crecieron durante años y ya no son fáciles de comparar. La app reconoce nombres distintos para una misma prueba, compara un estudio nuevo contra el último registro, separa valores fuera de rango de posibles errores de datos y permite preguntar sobre el expediente mostrando la evidencia que usó. No diagnostica: hace la información más navegable, auditable y verificable.

## Demo de 3 minutos

1. **Home** — explicar el problema y las capas de IA.
2. **Comparar estudio** — activar el estudio de demo.
3. Mostrar `GLU → Glucosa`, `Creat → Creatinina`, `Hb → Hemoglobina` y el registro sin match.
4. Enseñar `Qué cambió más` y aclarar que el porcentaje no es gravedad clínica.
5. **Signal vs. Noise** — mostrar diferencia entre rango y calidad de datos.
6. **Ask LabLens** — preguntar: `¿Qué datos tienen banderas de calidad?`
7. Abrir `Evidencia recuperada`.
8. Cerrar con: **La IA no decide qué significa un resultado; ayuda a encontrar qué merece ser revisado y por qué.**

## Preguntas que pueden hacer en clase

**¿Dónde está la IA?**  
En el matching aproximado de nombres, retrieval NLP y la capa LLM opcional. Las reglas matemáticas se identifican como reglas, no se maquillan de IA.

**¿Por qué no diagnostica?**  
Porque el objetivo del proyecto es organización y calidad de datos; una interpretación clínica requiere contexto que el expediente por sí solo no contiene.

**¿Qué harías en una fase 2?**  
Conectar el libro histórico completo, agregar unidades canónicas, evaluar matching con datos etiquetados y autenticar usuarios para manejar información privada.
