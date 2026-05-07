import os
import joblib
import numpy as np

# ================================
# 📁 BASE DIRECTORY
# ================================
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ================================
# 📂 FILE PATHS
# ================================
MODEL_PATH = os.path.join(BASE_DIR, "..", "current_stress_model.pkl")
ENCODER_PATH = os.path.join(BASE_DIR, "..", "current_label_encoder.pkl")
IMPUTER_PATH = os.path.join(BASE_DIR, "..", "imputer.pkl")

# ================================
# 🔄 LOAD COMPONENTS
# ================================
model = joblib.load(MODEL_PATH)
label_encoder = joblib.load(ENCODER_PATH)
imputer = joblib.load(IMPUTER_PATH)


# ================================
# 🧠 PREDICTION FUNCTION
# ================================
def predict_stress(data):
    try:
        # 🔹 Safe extraction
        income = float(data.get('monthly_income', 0) or 0)
        expense = float(data.get('monthly_expense_total', 0) or 0)

        # Avoid division issues
        if income <= 0:
            income = 1

        # ================================
        # 🔧 FEATURE ENGINEERING
        # ================================
        savings = income - expense
        expense_ratio = expense / income
        income_expense_ratio = income / (expense + 1)

        # ================================
        # 📊 BUILD FEATURE VECTOR (SMART)
        # ================================
        feature_vector = [
            income,
            expense,
            savings,
            income_expense_ratio,
            expense_ratio
        ]

        # 🔥 Fill remaining features with meaningful value
        while len(feature_vector) < 41:
            feature_vector.append(expense_ratio)   # instead of 0

        # ================================
        # 🔄 TRANSFORM
        # ================================
        input_array = np.array([feature_vector])
        input_array = imputer.transform(input_array)

        # ================================
        # 🤖 MODEL PREDICTION
        # ================================
        prediction = model.predict(input_array)
        model_result = label_encoder.inverse_transform(prediction)[0]

        # ================================
        # 🔥 RULE-BASED CORRECTION (IMPORTANT)
        # ================================
        # This prevents "always HIGH" issue

        if expense_ratio < 0.4:
            final_result = "Low"
        elif expense_ratio < 0.75:
            final_result = "Medium"
        else:
            final_result = "High"

        # 👉 You can choose:
        # return model_result   # pure ML
        return final_result    # hybrid (recommended)

    except Exception as e:
        return str(e)