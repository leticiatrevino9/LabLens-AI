import pandas as pd
from labcore import match_parameter, parse_reference_range, classify_value, compare_study

canonical = ["Glucosa", "Creatinina", "Colesterol LDL", "Hemoglobina"]

assert match_parameter("GLU", canonical)[0] == "Glucosa"
assert match_parameter("Creat", canonical)[0] == "Creatinina"
assert match_parameter("LDL colesterol", canonical)[0] == "Colesterol LDL"
assert match_parameter("Hb", canonical)[0] == "Hemoglobina"
assert parse_reference_range("70 - 110")[:2] == (70.0, 110.0)
assert classify_value(116, "70 - 110") == "Fuera"
assert classify_value(96, "<100") == "Dentro"
assert classify_value(71, ">60") == "Dentro"

base = pd.DataFrame([
    {"parametro":"Glucosa","periodo":"2026-05","ultimo_valor":108,"rango_transcrito":"70 - 110","comparacion":"Dentro","seccion":"Q"}
])
new = pd.DataFrame([{"prueba":"GLU","valor":116,"unidad":"mg/dL","rango":"70 - 110"}])
out = compare_study(new, base)
assert out.iloc[0]["parametro"] == "Glucosa"
assert out.iloc[0]["delta"] == 8.0
print("All LabLens core tests passed.")
