import math
import re
import unicodedata
from difflib import SequenceMatcher

import pandas as pd

ALIASES = {
    "glucosa": ["glu", "glucose", "glucosa sanguinea", "glucemia"],
    "creatinina": ["creat", "creatinine", "creatinina serica"],
    "colesterol total": ["chol", "cholesterol", "col total", "colesterol"],
    "colesterol ldl": ["ldl", "ldl colesterol", "ldl-c", "c-ldl"],
    "colesterol hdl": ["hdl", "hdl colesterol", "hdl-c", "c-hdl"],
    "triglicéridos": ["trigliceridos", "tg", "triglycerides"],
    "hemoglobina": ["hb", "hgb", "hemoglobin"],
    "hematocrito": ["hto", "hct", "hematocrit"],
    "eritrocitos": ["rbc", "eritrocitos totales", "globulos rojos"],
    "leucocitos": ["wbc", "leucocitos totales", "globulos blancos"],
    "lipasa en suero": ["lipasa", "lipase", "lipasa serica"],
    "amilasa en suero": ["amilasa", "amylase", "amilasa serica"],
    "ácido úrico": ["acido urico", "uric acid", "urato"],
    "sodio": ["na", "sodium"],
    "potasio": ["k", "potassium"],
    "tasa de filtración glomerular": ["egfr", "tfg", "filtracion glomerular"],
    "albúmina": ["albumina", "alb"],
    "globulina total": ["globulina", "globulin"],
    "alt": ["tgp", "alanina aminotransferasa"],
    "ast": ["tgo", "aspartato aminotransferasa"],
}


def normalize_text(value):
    text = "" if value is None else str(value)
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _alias_forms(canonical):
    forms = {normalize_text(canonical)}
    for alias in ALIASES.get(canonical.lower(), []):
        forms.add(normalize_text(alias))
    return forms


def match_parameter(raw_name, canonical_names, threshold=0.58):
    raw = normalize_text(raw_name)
    if not raw:
        return None, 0.0

    best_name, best_score = None, 0.0
    raw_tokens = set(raw.split())
    for canonical in canonical_names:
        forms = _alias_forms(canonical)
        for form in forms:
            score = SequenceMatcher(None, raw, form).ratio()
            form_tokens = set(form.split())
            if raw_tokens and form_tokens:
                jaccard = len(raw_tokens & form_tokens) / len(raw_tokens | form_tokens)
                score = max(score, jaccard)
            if raw == form:
                score = 1.0
            if score > best_score:
                best_name, best_score = canonical, score

    return (best_name, float(best_score)) if best_score >= threshold else (None, float(best_score))


def parse_reference_range(text):
    if text is None or (isinstance(text, float) and math.isnan(text)):
        return None, None, "none"
    s = str(text).lower().strip().replace(",", ".")
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r"\s+", "", s)

    m = re.search(r"(-?\d+(?:\.\d+)?)-(-?\d+(?:\.\d+)?)", s)
    if m:
        return float(m.group(1)), float(m.group(2)), "between"
    m = re.search(r"(?:<|menor(?:que)?|hasta)(-?\d+(?:\.\d+)?)", s)
    if m:
        return None, float(m.group(1)), "max"
    m = re.search(r"(?:>|mayor(?:que)?)(-?\d+(?:\.\d+)?)", s)
    if m:
        return float(m.group(1)), None, "min"
    return None, None, "none"


def classify_value(value, range_text):
    try:
        v = float(value)
    except (TypeError, ValueError):
        return "No evaluable"
    low, high, kind = parse_reference_range(range_text)
    if kind == "between":
        return "Dentro" if low <= v <= high else "Fuera"
    if kind == "max":
        return "Dentro" if v < high else "Fuera"
    if kind == "min":
        return "Dentro" if v > low else "Fuera"
    return "Sin rango"


def compare_study(new_df, baseline_df):
    canonical_names = baseline_df["parametro"].tolist()
    rows = []
    for _, row in new_df.iterrows():
        raw_name = row.get("prueba", row.get("parametro", ""))
        match, score = match_parameter(raw_name, canonical_names)
        try:
            new_value = float(row.get("valor"))
        except (TypeError, ValueError):
            new_value = None

        item = {
            "prueba_original": raw_name,
            "parametro": match or "Sin match",
            "confianza_match": round(score, 2),
            "valor_nuevo": new_value,
            "unidad_nueva": row.get("unidad", ""),
            "rango_nuevo": row.get("rango", ""),
            "estado_nuevo": classify_value(new_value, row.get("rango", "")) if new_value is not None else "No evaluable",
            "valor_previo": None,
            "periodo_previo": None,
            "delta": None,
            "delta_pct": None,
            "revision_datos": "Revisar match" if match is None else "OK",
        }
        if match:
            prev = baseline_df[baseline_df["parametro"] == match].iloc[0]
            try:
                prev_value = float(prev["ultimo_valor"])
            except (TypeError, ValueError):
                prev_value = None
            item["valor_previo"] = prev_value
            item["periodo_previo"] = prev.get("periodo")
            if prev_value is not None and new_value is not None:
                delta = new_value - prev_value
                item["delta"] = round(delta, 3)
                if prev_value != 0:
                    item["delta_pct"] = round(delta / abs(prev_value) * 100, 1)
            if score < 0.78:
                item["revision_datos"] = "Confirmar nombre"
            if item["estado_nuevo"] == "Fuera":
                item["revision_datos"] = "Verificar rango / contexto"
        rows.append(item)
    return pd.DataFrame(rows)


def summarize_changes(compared_df):
    matched = compared_df[compared_df["parametro"] != "Sin match"]
    unmatched = compared_df[compared_df["parametro"] == "Sin match"]
    outside = matched[matched["estado_nuevo"] == "Fuera"]
    changed = matched[matched["delta_pct"].notna()].copy()
    if not changed.empty:
        changed["abs_delta_pct"] = changed["delta_pct"].abs()
        changed = changed.sort_values("abs_delta_pct", ascending=False)
    return {
        "matched": len(matched),
        "unmatched": len(unmatched),
        "outside": len(outside),
        "largest_changes": changed.head(5),
    }
