import os
import re
import pandas as pd
import torch
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM

# ========== Label Mappings ==========

label2id = {
    "not eligible": 0,
    "eligible": 1,
    "eligible for some": 2,
    "eligible for most": 3
}
id2label = {v: k for k, v in label2id.items()}

# ========== Helpers ==========

def format_patient_profile(patient: dict) -> str:
    return "\n".join([f"{k}: {v}" for k, v in patient.items()])

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

# ========== Prediction ==========

def predict_eligibility(patient, trials, tokenizer, model, device):
    profile_dict = patient.to_dict()
    patient_str = format_patient_profile(profile_dict)

    results = []

    for trial in trials:
        trial_name = trial.get("Name", "Unnamed Trial")
        inc = "\n- " + "\n- ".join(trial.get("Inclusion Criteria", [])[:6])
        exc = "\n- " + "\n- ".join(trial.get("Exclusion Criteria", [])[:6])

        input_text = f"""Patient Profile:
{patient_str}

Trial: {trial_name}
Inclusion Criteria:{inc}
Exclusion Criteria:{exc}
"""

        inputs = tokenizer(
            input_text,
            return_tensors="pt",
            truncation=True,
            padding="max_length",
            max_length=512
        ).to(device)

        outputs = model.generate(**inputs, max_new_tokens=10)
        prediction = tokenizer.decode(outputs[0], skip_special_tokens=True).strip().lower()
        results.append(prediction)

    # Count how many trials were predicted eligible
    eligible_count = sum(1 for r in results if "eligible" in r and "not" not in r)

    if eligible_count == 0:
        return "Not Eligible"
    elif eligible_count < len(trials) * 0.5:
        return "Eligible for Some"
    else:
        return "Eligible for Most"

# ========== Main ==========

def main():
    model_path = "./t5_trial_matcher"
    csv_path = "patients_data/testing_dataset.csv"
    trials_folder = "trials_data"

    print("📦 Loading model...")
    tokenizer = AutoTokenizer.from_pretrained(model_path)
    model = AutoModelForSeq2SeqLM.from_pretrained(model_path)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device)
    model.eval()

    print("📋 Loading patient and trial data...")
    test_df = pd.read_csv(csv_path)
    trials = load_trials(trials_folder)

    print("🔍 Running predictions...")
    predictions = []
    for i, patient in test_df.iterrows():
        pred = predict_eligibility(patient, trials, tokenizer, model, device)
        predictions.append(pred)
        print(f"[{i+1}/{len(test_df)}] → {pred}")

    test_df["predicted_label"] = predictions

    print("\n✅ Prediction complete!")
    print(test_df[["eligibility_label", "predicted_label"]].head())

    # Optional: Save results
    output_path = "predictions_on_test.csv"
    test_df.to_csv(output_path, index=False)
    print(f"📁 Results saved to: {output_path}")

if __name__ == "__main__":
    main()
