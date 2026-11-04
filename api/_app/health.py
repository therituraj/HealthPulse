"""Form definitions, validation, model-feature encoding and display rows for both report types."""
import math

YES_NO = {"0": "No", "1": "Yes"}
LEVELS = {"1": "Normal", "2": "Above normal", "3": "High"}

# Encodings used when the diabetes model was trained (LabelEncoder, alphabetical order).
# If your training code used different codes, change them here only.
DIABETES_GENDER = {"Female": 0, "Male": 1}
DIABETES_SMOKING = {"No Info": 0, "current": 1, "ever": 2, "former": 3, "never": 4, "not current": 5}

P, M, B, L = "Personal details", "Medical history", "Blood test results", "Lifestyle"
BP = "Blood pressure and blood tests"


def _num(key, label, section, lo, hi, unit="", integer=False):
    return dict(key=key, label=label, section=section, kind="number", min=lo, max=hi, unit=unit, integer=integer)


def _choice(key, label, section, choices):
    return dict(key=key, label=label, section=section, kind="choice", choices=choices)


FIELDS = {
    "diabetes": [
        _choice("gender", "Gender", P, {"Female": "Female", "Male": "Male"}),
        _num("age", "Age", P, 1, 120, "years"),
        _choice("smokingHistory", "Smoking history", P, {
            "No Info": "No info", "never": "Never smoked", "former": "Former smoker",
            "current": "Current smoker", "not current": "Not a current smoker", "ever": "Has smoked before"}),
        _num("bmi", "BMI", P, 10, 100, "kg/m²"),
        _choice("hypertension", "Hypertension", M, YES_NO),
        _choice("heart_disease", "Heart disease", M, YES_NO),
        _num("hba1cLevel", "HbA1c level", B, 3, 15, "%"),
        _num("bloodGlucoseLevel", "Blood glucose level", B, 50, 400, "mg/dL", integer=True),
    ],
    "heart": [
        _num("age", "Age", P, 1, 120, "years", integer=True),
        _choice("gender", "Gender", P, {"1": "Female", "2": "Male"}),
        _num("height", "Height", P, 100, 250, "cm"),
        _num("weight", "Weight", P, 30, 300, "kg"),
        _num("ap_hi", "Systolic blood pressure", BP, 70, 250, "mmHg", integer=True),
        _num("ap_lo", "Diastolic blood pressure", BP, 40, 200, "mmHg", integer=True),
        _choice("cholesterol", "Cholesterol level", BP, LEVELS),
        _choice("gluc", "Glucose level", BP, LEVELS),
        _choice("smoke", "Smoker", L, YES_NO),
        _choice("alco", "Drinks alcohol", L, YES_NO),
        _choice("active", "Physically active", L, YES_NO),
    ],
}

RESULT_TEXT = {
    "diabetes": ("Higher risk of diabetes detected", "Lower risk of diabetes detected"),
    "heart": ("Higher risk of heart disease detected", "Lower risk of heart disease detected"),
}


def validate(kind, form):
    """Return (clean_values, error_messages)."""
    clean, errors = {}, []
    for f in FIELDS[kind]:
        raw = (form.get(f["key"]) or "").strip()
        if not raw:
            errors.append(f"{f['label']} is required.")
            continue
        if f["kind"] == "choice":
            if raw not in f["choices"]:
                errors.append(f"Please choose a valid option for {f['label']}.")
                continue
            clean[f["key"]] = raw
            continue
        try:
            val = float(raw)
        except ValueError:
            errors.append(f"{f['label']} must be a number.")
            continue
        if not math.isfinite(val) or val < f["min"] or val > f["max"]:
            errors.append(f"{f['label']} must be between {f['min']:g} and {f['max']:g}.")
            continue
        clean[f["key"]] = int(round(val)) if f["integer"] else val
    if kind == "heart" and not errors and clean["ap_hi"] <= clean["ap_lo"]:
        errors.append("Systolic pressure must be higher than diastolic pressure.")
    return clean, errors


def features(kind, c, age_in_days=False):
    """Build the numeric vector in the exact column order the models expect."""
    if kind == "diabetes":
        return [
            DIABETES_GENDER[c["gender"]], c["age"], int(c["hypertension"]), int(c["heart_disease"]),
            DIABETES_SMOKING[c["smokingHistory"]], c["bmi"], c["hba1cLevel"], c["bloodGlucoseLevel"],
        ]
    age = round(c["age"] * 365.25) if age_in_days else c["age"]
    return [
        age, int(c["gender"]), c["height"], c["weight"], c["ap_hi"], c["ap_lo"],
        int(c["cholesterol"]), int(c["gluc"]), int(c["smoke"]), int(c["alco"]), int(c["active"]),
    ]


def _show(f, value):
    if f["kind"] == "choice":
        return f["choices"].get(str(value), str(value))
    text = f"{value:g}"
    return f"{text} {f['unit']}".strip()


def grouped_rows(kind, inputs):
    """[(section, [(label, value_text), ...]), ...] in display order. Missing keys are skipped."""
    sections = {}
    for f in FIELDS[kind]:
        if f["key"] in inputs:
            sections.setdefault(f["section"], []).append((f["label"], _show(f, inputs[f["key"]])))
    if kind == "heart" and "height" in inputs and "weight" in inputs:
        bmi = inputs["weight"] / ((inputs["height"] / 100) ** 2)
        sections.setdefault(P, []).append(("BMI (calculated)", f"{bmi:.1f} kg/m²"))
    return list(sections.items())
