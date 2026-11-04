Put your trained models here (they are bundled by vercel.json "includeFiles"):

- Diabetes_Prediction_Logistic_Regression_Model.pkl
- Heart_Disease_Prediction_Model.pkl   (rename via HEART_MODEL_FILE in .env if yours differs)

Feature order the app sends:
- diabetes: gender, age, hypertension, heart_disease, smoking_history, bmi, HbA1c_level, blood_glucose_level
- heart:    age, gender, height, weight, ap_hi, ap_lo, cholesterol, gluc, smoke, alco, active
Category codes live in api/_app/health.py (DIABETES_GENDER / DIABETES_SMOKING).
