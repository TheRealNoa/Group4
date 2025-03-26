# file: patient_trial_matcher.py

import os
import re
import difflib
import pandas as pd
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.model_selection import train_test_split
import seaborn as sns
import matplotlib.pyplot as plt

# ==================== CONFIGURATION ====================

FIELD_KEYWORDS = {
    "ECOGPerformanceStatus": ["ecog", "performance status"],
    "GeneticMutations": ["mutation", "brca", "tp53"],
    "Comorbidities": ["hypertension", "diabetes", "cardiac"],
    "OrganFunctionStatus": ["organ", "liver", "kidney", "renal"],
    "PreviousCancerHistory": ["previous cancer", "prior cancer"],
    "PresenceOfMetastases": ["metastatic", "stage iv", "metastases"],
    "PregnancyBreastfeedingStatus": ["pregnancy", "pregnant", "breastfeeding"],
    "Age": ["age", "years old"],
    "Diagnosis": ["diagnosis", "tumor", "carcinoma"],
    "Gender": ["female", "male"],
    "TreatmentHistory": ["chemotherapy", "radiotherapy", "treatment history"]
}

EXCLUSION_NOISE = [
    "ages eligible", "sexes eligible", "healthy volunteers", "show less",
    "sampling method", "study population", "gender eligibility"
]

# ==================== DATA HELPERS ====================

def load_patient_csv(csv_path):
    df = pd.read_csv(csv_path)
    return train_test_split(df, test_size=10, stratify=df["eligibility_label"], random_state=42)

def format_patient_profile(patient: dict) -> str:
    return "\n".join([f"{k}: {v}" for k, v in patient.items()])

# ==================== TRIAL LOADING ====================

def read_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        return file.read()

def parse_document(document):
    key_value_pattern = re.compile(r'^([^,:]+):,(.*)$')
    section_pattern = re.compile(r'-{50,}')
    data = {}
    for line in document.split('\n'):
        if section_pattern.match(line):
            continue
        elif key_value_pattern.match(line):
            key, val = key_value_pattern.match(line).groups()
            data[key.strip()] = val.strip()
        elif line.strip() and list(data):
            last_key = list(data)[-1]
            data[last_key] += ' ' + line.strip()
    return data

def split_criteria(section):
    return [c.strip() for c in re.split(r'\.\s*', section) if c.strip()]

def process_trial_file(file_path):
    doc = read_file(file_path)
    data = parse_document(doc)
    eligibility = data.get("Eligibility Criteria", "")
    if "||" in eligibility:
        inc, exc = eligibility.split("||")
    else:
        inc, exc = eligibility, ""
    data["Inclusion Criteria"] = split_criteria(inc.replace("Inclusion:", "").strip())
    data["Exclusion Criteria"] = split_criteria(exc.replace("Exclusion:", "").strip())
    return data

def load_trials(folder_path):
    return [
        process_trial_file(os.path.join(folder_path, f))
        for f in os.listdir(folder_path)
        if f.endswith(".csv")
    ]

# ==================== MATCHING LOGIC ====================

def clean_criteria_list(criteria):
    return [c for c in criteria if not any(p in c.lower() for p in EXCLUSION_NOISE)]

def smart_semantic_match(patient: dict, criteria):
    matched = []
    cleaned_criteria = clean_criteria_list(criteria)

    for field, value in patient.items():
        if not isinstance(value, str) or not value.strip():
            continue
        keywords = FIELD_KEYWORDS.get(field, [])
        for rule in cleaned_criteria:
            rule_lower = rule.lower()
            for keyword in keywords:
                if keyword in rule_lower:
                    score = difflib.SequenceMatcher(None, value.lower(), rule_lower).ratio()
                    if value.lower() in rule_lower or score > 0.9:
                        matched.append((field, value, rule))
                        break
    return matched

def evaluate_trial_match(patient_str, patient_dict, trial, tokenizer, model):
    trial_name = trial.get("Name", "Unnamed Trial")
    inc = trial.get("Inclusion Criteria", [])
    exc = trial.get("Exclusion Criteria", [])

    matched_exc = smart_semantic_match(patient_dict, exc)
    if matched_exc:
        return "Not Eligible"

    inc_display = "\n- " + "\n- ".join(inc[:8])
    exc_display = "\n- " + "\n- ".join(exc[:8])
    prompt = f"""
You are a clinical trial eligibility expert.

Based on the patient's profile and trial criteria, determine if the patient is eligible. Use this format:

Matched Inclusion Criteria:
- [PatientField: Value] ↔ [Trial Inclusion: Text]

Unmatched or Violated Criteria:
- ...

Conclusion:
Eligible / Not Eligible with reason

### Patient Profile:
{patient_str}

### Trial: {trial_name}
Inclusion Criteria:{inc_display}

Exclusion Criteria:{exc_display}

Answer:
"""
    inputs = tokenizer(prompt, return_tensors="pt", truncation=True, max_length=1024)
    outputs = model.generate(inputs["input_ids"], max_length=512, num_beams=5, early_stopping=True)
    explanation = tokenizer.decode(outputs[0], skip_special_tokens=True).strip()

    explanation_lower = explanation.lower()
    if "not eligible" in explanation_lower:
        return "Not Eligible"
    elif "eligible" in explanation_lower:
        return "Eligible"
    else:
        return "Not Eligible"

# ==================== MAIN ====================

def main():
    csv_path = "patients_data/testing_dataset.csv"
    trials_folder = "trials_data"
    model_name = "google/flan-t5-base"

    print("🔄 Loading model...")
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForSeq2SeqLM.from_pretrained(model_name)

    print("📋 Loading patient and trial data...")
    train_df = pd.read_csv('patients_data/synthetic_balanced_split.csv')
    test_df = pd.read_csv('patients_data/testing_dataset.csv')
    trials = load_trials(trials_folder)

    def predict_label(patient):
        profile_dict = patient.to_dict()
        patient_str = format_patient_profile(profile_dict)
        match_count = sum(
            1 for trial in trials
            if evaluate_trial_match(patient_str, profile_dict, trial, tokenizer, model) == "Eligible"
        )
        if match_count == 0:
            return "Not Eligible"
        elif match_count < len(trials) * 0.5:
            return "Eligible for Some"
        else:
            return "Eligible for Most"

    print("🔬 Evaluating validation set...")
    test_df["predicted_label"] = test_df.apply(predict_label, axis=1)
    print("\n📊 Classification Report:")
    print(classification_report(test_df["eligibility_label"], test_df["predicted_label"]))

    cm = confusion_matrix(test_df["eligibility_label"], test_df["predicted_label"], labels=["Not Eligible", "Eligible for Some", "Eligible for Most"])
    sns.heatmap(cm, annot=True, fmt="d", xticklabels=["Not Eligible", "Some", "Most"], yticklabels=["Not Eligible", "Some", "Most"])
    plt.xlabel("Predicted")
    plt.ylabel("True")
    plt.title("Confusion Matrix")
    plt.show()

if __name__ == "__main__":
    main()