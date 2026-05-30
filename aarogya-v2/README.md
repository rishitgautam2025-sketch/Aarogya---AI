# Aarogya AI V2

Two-sided health intelligence platform. Disease triage, injury assessment, and aging parent care coordination for 500M Indians with limited healthcare access.

---

## Setup

```bash
pip install -r requirements.txt
```

**Get the dataset:**
Download `Training.csv` from Kaggle — [Pranay Patil: Disease Symptom Prediction](https://www.kaggle.com/datasets/itachi9604/disease-symptom-description-dataset)
Place it at `data/Training.csv`.

**Train the model:**
```bash
python model/train.py
```
This will compare Naive Bayes, Random Forest, and XGBoost, then save the best model to `model/best_model.pkl`.

**Start the API:**
```bash
uvicorn api.main:app --reload --port 8000
```

**Interactive docs:** `http://localhost:8000/docs`

---

## API Reference

### `GET /health`
Returns model status, disease count, and version.

### `GET /symptoms`
Returns the full list of 132 recognized symptom names.

### `GET /diseases`
Returns all 41 disease classes the model can predict.

### `POST /predict`
Disease triage from symptom list.

**Request:**
```json
{
  "symptoms": ["high_fever", "headache", "chills", "sweating"],
  "age": 72,
  "sex": "male"
}
```

**Response:**
```json
{
  "risk_level": "RED",
  "top_predictions": [
    {"disease": "Malaria", "confidence": 0.91, "confidence_label": "HIGH"},
    {"disease": "Dengue", "confidence": 0.06, "confidence_label": "LOW"},
    {"disease": "Typhoid", "confidence": 0.02, "confidence_label": "LOW"}
  ],
  "unclear": false,
  "disclaimer": "...",
  "next_steps": ["Seek emergency medical care immediately.", "..."],
  "unrecognized_symptoms": []
}
```

Risk levels: `RED` (emergency), `YELLOW` (visit doctor within 48h), `GREEN` (routine care).
If `unclear: true` (top confidence < 60%), the model recommends asking more clarifying questions.
Age 65+ triggers upward risk escalation automatically.

### `POST /predict/injury`
Injury triage using Ottawa Ankle Rules, Ottawa Knee Rules, and general fracture indicators.

**Request (ankle injury):**
```json
{
  "body_part": "ankle",
  "mechanism": "twist",
  "can_weight_bear": false,
  "immediate_swelling": true,
  "point_tenderness": true,
  "audible_crack": false,
  "range_of_motion_lost": false,
  "bruising_present": true,
  "tenderness_lateral_malleolus": true
}
```

**Body parts:** `ankle`, `foot`, `knee`, `wrist`, `neck`, `general`
**Mechanisms:** `twist`, `direct_impact`, `fall`, `unknown`

**Response:**
```json
{
  "fracture_probability": "HIGH",
  "clinical_rule_applied": "Ottawa Ankle/Foot Rules",
  "findings": ["Tenderness at lateral malleolus — Ottawa Ankle Rule positive", "..."],
  "recommendation": "HIGH fracture probability. Go to an emergency room now...",
  "action_steps": ["Do not walk on or use the injured limb.", "..."],
  "disclaimer": "This is a preliminary assessment only..."
}
```

### `POST /feedback`
Log user feedback for retraining.

```json
{
  "session_id": "abc123",
  "predicted_disease": "Malaria",
  "actual_diagnosis": "Dengue",
  "was_helpful": true
}
```

---

## Model Comparison (Synthetic Data)

| Model | Accuracy | F1 | CV Mean |
|---|---|---|---|
| Naive Bayes | 60.7% | 60.4% | 65.1% |
| Random Forest | **97.3%** | **97.3%** | **97.5%** |
| XGBoost | 96.9% | 96.8% | 97.3% |

Note: These numbers are on synthetic data. Real Kaggle dataset accuracy is typically 97-99% for Random Forest. Naive Bayes is lower because the dataset violates its independence assumption (symptoms within a disease are correlated).

---

## Next Build Steps

1. **Injury module** - done (Ottawa Rules implemented)
2. **Parent Health Dashboard** - aging parent care coordinator
3. **Medication manager** - WhatsApp reminders via Twilio
4. **Voice input** - Web Speech API / Whisper for Hindi
5. **ASHA worker upgrade** - time-series anomaly detection for outbreak alerts
6. **WhatsApp interface** - alternative entry point for low-smartphone-literacy users

---

## Clinical Logic

**Injury Triage:**
- Ottawa Ankle Rules: validated clinical decision rules with >95% sensitivity for ruling out fractures
- Ottawa Knee Rules: age, patella/fibula tenderness, weight bearing, ROM
- General indicators: swelling timeline, mechanism, point tenderness, audible crack

**Disease Triage:**
- Risk stratification into RED/YELLOW/GREEN based on disease class
- Age-adjusted escalation: symptoms in 65+ patients automatically escalate one tier
- Unclear flag triggers when top prediction confidence < 60%

**Disclaimer:** All outputs are preliminary AI assessments. Not a substitute for professional medical evaluation.

---

## Data Privacy

- No identifiable health data stored without consent
- Feedback is anonymized (session_id only, no name/phone)
- Community insights use aggregated, non-identifiable data only

---

## Stack

- **ML:** Python, scikit-learn (Random Forest), XGBoost
- **API:** FastAPI + Uvicorn
- **Storage:** PostgreSQL / Supabase (Phase 2)
- **Deploy:** Railway / Render free tier

Built for India. Rs-sensitive architecture. Designed for 2G constraints.
