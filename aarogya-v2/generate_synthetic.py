"""
Generates a synthetic Training.csv matching the exact schema of:
Pranay Patil — Disease Symptom Prediction (Kaggle)

This is for testing the pipeline only.
Replace with the real Training.csv before production use.
"""

import numpy as np
import pandas as pd
from pathlib import Path

np.random.seed(42)

DISEASES = [
    "Fungal infection", "Allergy", "GERD", "Chronic cholestasis",
    "Drug Reaction", "Peptic ulcer disease", "AIDS", "Diabetes",
    "Gastroenteritis", "Bronchial Asthma", "Hypertension", "Migraine",
    "Cervical spondylosis", "Paralysis (brain hemorrhage)", "Jaundice",
    "Malaria", "Chicken pox", "Dengue", "Typhoid", "hepatitis A",
    "Hepatitis B", "Hepatitis C", "Hepatitis D", "Hepatitis E",
    "Alcoholic hepatitis", "Tuberculosis", "Common Cold", "Pneumonia",
    "Dimorphic hemorrhoids (piles)", "Heart attack", "Varicose veins",
    "Hypothyroidism", "Hyperthyroidism", "Hypoglycemia", "Osteoarthritis",
    "Arthritis", "(Vertigo) Paroxysmal Positional Vertigo", "Acne",
    "Urinary tract infection", "Psoriasis", "Impetigo"
]

SYMPTOMS = [
    "itching", "skin_rash", "nodal_skin_eruptions", "continuous_sneezing",
    "shivering", "chills", "joint_pain", "stomach_pain", "acidity",
    "ulcers_on_tongue", "muscle_wasting", "vomiting", "burning_micturition",
    "spotting_urination", "fatigue", "weight_gain", "anxiety",
    "cold_hands_and_feets", "mood_swings", "weight_loss", "restlessness",
    "lethargy", "patches_in_throat", "irregular_sugar_level", "cough",
    "high_fever", "sunken_eyes", "breathlessness", "sweating", "dehydration",
    "indigestion", "headache", "yellowish_skin", "dark_urine",
    "nausea", "loss_of_appetite", "pain_behind_the_eyes", "back_pain",
    "constipation", "abdominal_pain", "diarrhoea", "mild_fever",
    "yellow_urine", "yellowing_of_eyes", "acute_liver_failure",
    "fluid_overload", "swelling_of_stomach", "swelled_lymph_nodes",
    "malaise", "blurred_and_distorted_vision", "phlegm", "throat_irritation",
    "redness_of_eyes", "sinus_pressure", "runny_nose", "congestion",
    "chest_pain", "weakness_in_limbs", "fast_heart_rate",
    "pain_during_bowel_movements", "pain_in_anal_region", "bloody_stool",
    "irritation_in_anus", "neck_pain", "dizziness", "cramps",
    "bruising", "obesity", "swollen_legs", "swollen_blood_vessels",
    "puffy_face_and_eyes", "enlarged_thyroid", "brittle_nails",
    "swollen_extremeties", "excessive_hunger", "extra_marital_contacts",
    "drying_and_tingling_lips", "slurred_speech", "knee_pain",
    "hip_joint_pain", "muscle_weakness", "stiff_neck", "swelling_joints",
    "movement_stiffness", "spinning_movements", "loss_of_balance",
    "unsteadiness", "weakness_of_one_body_side", "loss_of_smell",
    "bladder_discomfort", "foul_smell_of_urine", "continuous_feel_of_urine",
    "passage_of_gases", "internal_itching", "toxic_look_(typhos)",
    "depression", "irritability", "muscle_pain", "altered_sensorium",
    "red_spots_over_body", "belly_pain", "abnormal_menstruation",
    "dischromic_patches", "watering_from_eyes", "increased_appetite",
    "polyuria", "family_history", "mucoid_sputum", "rusty_sputum",
    "lack_of_concentration", "visual_disturbances", "receiving_blood_transfusion",
    "receiving_unsterile_injections", "coma", "stomach_bleeding",
    "distention_of_abdomen", "history_of_alcohol_consumption",
    "fluid_overload.1", "blood_in_sputum", "prominent_veins_on_calf",
    "palpitations", "painful_walking", "pus_filled_pimples",
    "blackheads", "scurring", "skin_peeling", "silver_like_dusting",
    "small_dents_in_nails", "inflammatory_nails", "blister",
    "red_sore_around_nose", "yellow_crust_ooze"
]

# Disease-to-symptom affinity map (simplified but directionally correct)
DISEASE_SYMPTOMS = {
    "Fungal infection": ["itching", "skin_rash", "nodal_skin_eruptions", "dischromic_patches"],
    "Allergy": ["continuous_sneezing", "shivering", "chills", "watering_from_eyes", "redness_of_eyes"],
    "GERD": ["acidity", "ulcers_on_tongue", "vomiting", "cough", "chest_pain"],
    "Diabetes": ["fatigue", "weight_loss", "polyuria", "increased_appetite", "irregular_sugar_level"],
    "Hypertension": ["headache", "chest_pain", "dizziness", "fast_heart_rate"],
    "Malaria": ["high_fever", "chills", "sweating", "headache", "nausea", "vomiting"],
    "Dengue": ["high_fever", "pain_behind_the_eyes", "headache", "joint_pain", "skin_rash", "red_spots_over_body"],
    "Typhoid": ["high_fever", "vomiting", "fatigue", "toxic_look_(typhos)", "abdominal_pain"],
    "Common Cold": ["continuous_sneezing", "runny_nose", "congestion", "mild_fever", "cough", "throat_irritation"],
    "Pneumonia": ["cough", "high_fever", "breathlessness", "mucoid_sputum", "rusty_sputum", "chest_pain"],
    "Jaundice": ["yellowish_skin", "dark_urine", "yellowing_of_eyes", "fatigue", "nausea"],
    "Migraine": ["headache", "nausea", "vomiting", "blurred_and_distorted_vision", "visual_disturbances"],
    "Heart attack": ["chest_pain", "fast_heart_rate", "breathlessness", "sweating", "vomiting"],
    "Urinary tract infection": ["burning_micturition", "bladder_discomfort", "foul_smell_of_urine", "continuous_feel_of_urine"],
    "Tuberculosis": ["cough", "high_fever", "weight_loss", "blood_in_sputum", "fatigue", "sweating"],
    "Acne": ["skin_rash", "pus_filled_pimples", "blackheads", "scurring"],
    "Psoriasis": ["skin_rash", "skin_peeling", "silver_like_dusting", "small_dents_in_nails", "inflammatory_nails"],
    "Impetigo": ["skin_rash", "blister", "red_sore_around_nose", "yellow_crust_ooze"],
    "Hypothyroidism": ["weight_gain", "fatigue", "cold_hands_and_feets", "enlarged_thyroid", "brittle_nails"],
    "Hyperthyroidism": ["weight_loss", "fast_heart_rate", "anxiety", "excessive_hunger", "sweating"],
    "Osteoarthritis": ["knee_pain", "hip_joint_pain", "movement_stiffness", "joint_pain"],
    "Arthritis": ["joint_pain", "swelling_joints", "movement_stiffness", "muscle_weakness"],
    "Gastroenteritis": ["vomiting", "diarrhoea", "abdominal_pain", "dehydration", "nausea"],
    "Peptic ulcer disease": ["stomach_pain", "acidity", "indigestion", "loss_of_appetite", "vomiting"],
    "Varicose veins": ["swollen_legs", "swollen_blood_vessels", "prominent_veins_on_calf", "painful_walking"],
    "Dimorphic hemorrhoids (piles)": ["pain_during_bowel_movements", "bloody_stool", "constipation", "pain_in_anal_region"],
    "Bronchial Asthma": ["breathlessness", "cough", "fatigue", "mucoid_sputum", "high_fever"],
    "Chicken pox": ["skin_rash", "itching", "high_fever", "lethargy", "vomiting", "blister"],
    "hepatitis A": ["yellowish_skin", "vomiting", "nausea", "abdominal_pain", "loss_of_appetite"],
    "Hepatitis B": ["yellowish_skin", "dark_urine", "fatigue", "loss_of_appetite", "receiving_blood_transfusion"],
    "Hepatitis C": ["yellowish_skin", "nausea", "fatigue", "loss_of_appetite", "receiving_unsterile_injections"],
    "Hepatitis D": ["yellowish_skin", "dark_urine", "joint_pain", "fatigue", "abdominal_pain"],
    "Hepatitis E": ["yellowish_skin", "vomiting", "nausea", "abdominal_pain", "acute_liver_failure"],
    "Alcoholic hepatitis": ["yellowish_skin", "vomiting", "abdominal_pain", "history_of_alcohol_consumption", "swelling_of_stomach"],
    "Chronic cholestasis": ["yellowish_skin", "itching", "dark_urine", "fatigue", "loss_of_appetite"],
    "AIDS": ["muscle_wasting", "patches_in_throat", "extra_marital_contacts", "high_fever", "fatigue"],
    "Drug Reaction": ["skin_rash", "itching", "burning_micturition", "fatigue", "anxiety"],
    "Cervical spondylosis": ["neck_pain", "dizziness", "back_pain", "weakness_in_limbs"],
    "Paralysis (brain hemorrhage)": ["weakness_of_one_body_side", "slurred_speech", "loss_of_balance", "headache"],
    "Hypoglycemia": ["excessive_hunger", "sweating", "drying_and_tingling_lips", "anxiety", "palpitations"],
    "(Vertigo) Paroxysmal Positional Vertigo": ["spinning_movements", "dizziness", "loss_of_balance", "unsteadiness", "nausea"],
}

SYMPTOM_INDEX = {s: i for i, s in enumerate(SYMPTOMS)}
N_SYMPTOMS = len(SYMPTOMS)
ROWS_PER_DISEASE = 120  # 41 * 120 = 4,920 total


def generate():
    rows = []
    for disease in DISEASES:
        core = DISEASE_SYMPTOMS.get(disease, SYMPTOMS[:4])
        for _ in range(ROWS_PER_DISEASE):
            row = np.zeros(N_SYMPTOMS, dtype=int)
            # Always include 3-4 core symptoms
            n_core = min(len(core), np.random.randint(3, len(core) + 1))
            for s in np.random.choice(core, n_core, replace=False):
                if s in SYMPTOM_INDEX:
                    row[SYMPTOM_INDEX[s]] = 1
            # Optionally add 0-2 random symptoms (noise)
            noise_count = np.random.randint(0, 3)
            for i in np.random.choice(N_SYMPTOMS, noise_count, replace=False):
                row[i] = 1
            rows.append(list(row) + [disease])

    df = pd.DataFrame(rows, columns=SYMPTOMS + ["prognosis"])
    df = df.sample(frac=1, random_state=42).reset_index(drop=True)
    return df


if __name__ == "__main__":
    out = Path(__file__).parent / "Training.csv"
    df = generate()
    df.to_csv(out, index=False)
    print(f"[SYNTHETIC] Generated {len(df)} rows → {out}")
    print(f"  Diseases: {df['prognosis'].nunique()} | Symptoms: {len(SYMPTOMS)}")
