import pandas as pd
import json

def load_trials(trial_path):
    with open(trial_path, 'r') as f:
        return json.load(f)

def load_patients(csv_path):
    return pd.read_csv(csv_path)

def check_eligibility(patient, trial):
    reasons = []
    eligible = True

    # Inclusion checks
    inc = trial["inclusion_criteria"]
    if "age_min" in inc and patient["age"] < inc["age_min"]:
        reasons.append(f"Age {patient['age']} < minimum {inc['age_min']}")
        eligible = False

    if "ecog_max" in inc and patient["ecog"] > inc["ecog_max"]:
        reasons.append(f"ECOG {patient['ecog']} > maximum {inc['ecog_max']}")
        eligible = False

    if "diagnosis" in inc and patient["diagnosis"] not in inc["diagnosis"]:
        reasons.append(f"Diagnosis {patient['diagnosis']} not in {inc['diagnosis']}")
        eligible = False

    if "staging" in inc and patient["stage"] not in inc["staging"]:
        reasons.append(f"Stage {patient['stage']} not eligible")
        eligible = False

    if "prior_treatment" in inc and patient["treatment_history"] not in inc["prior_treatment"]:
        reasons.append(f"Treatment history '{patient['treatment_history']}' not eligible")
        eligible = False

    if "measurable_disease" in inc:
        if inc["measurable_disease"] and not patient["measurable_disease"]:
            reasons.append("No measurable disease required for trial")
            eligible = False

    # Exclusion checks
    exc = trial["exclusion_criteria"]
    if "prior_treatment_lines" in exc:
        max_lines = int(exc["prior_treatment_lines"].replace(">", ""))
        if patient["prior_lines"] > max_lines:
            reasons.append(f"More than {max_lines} prior lines of treatment")
            eligible = False

    if "comorbidities" in exc:
        for condition in exc["comorbidities"]:
            if condition.lower() in patient["comorbidities"].lower():
                reasons.append(f"Excluded due to comorbidity: {condition}")
                eligible = False

    return eligible, reasons

def screen_all(patients_csv, trials_json):
    patients = load_patients(patients_csv)
    trials = load_trials(trials_json)

    for idx, patient in patients.iterrows():
        print(f"\n--- Patient {patient['patient_id']} ---")
        for trial in trials:
            eligible, reasons = check_eligibility(patient, trial)
            print(f"Trial: {trial['name']} --> {'✅ Eligible' if eligible else '❌ Ineligible'}")
            if reasons:
                for r in reasons:
                    print("   ↳", r)

# Run screening
if __name__ == "__main__":
    screen_all("patients.csv", "trials.json")
