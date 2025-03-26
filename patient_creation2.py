import pandas as pd
import random

# Define inclusion and exclusion keys
INCLUSION_KEYS = [
    "age_over_18", "triple_negative", "her2_negative",
    "ecog_0_1", "adequate_organ_function", "received_radiotherapy"
]

EXCLUSION_KEYS = [
    "no_metastasis",  # must be True
    "previous_cancer", "cardiac_condition", "brca_mutation",
    "prior_her2_treatment", "prior_endocrine_therapy",
    "active_infection", "pregnant_or_breastfeeding",
    "lvef_below_50", "arrhythmia", "ctla4_inhibitor",
    "cd137_agent", "ox40_agent", "topoisomerase_inhibitor"
]

# Fields that can safely vary (don't affect eligibility)
NOISE_KEYS = ["er_positive"]

def generate_patient(patient_id, eligible=True):
    patient = {}

    # Set inclusion fields
    for key in INCLUSION_KEYS:
        patient[key] = True if eligible else random.choice([True, False])

    # Set exclusion fields
    for key in EXCLUSION_KEYS:
        # Exclusion is based on being FALSE to be eligible
        if eligible:
            patient[key] = False  # safe default
        else:
            # For not eligible, randomly introduce violations
            patient[key] = random.choices([True, False], weights=[0.7, 0.3])[0]

    # Add noise/random fields (safe to vary)
    for key in NOISE_KEYS:
        patient[key] = random.choice([True, False])

    # Final fields
    patient["trial_name"] = "ASCENT-05"
    patient["eligibility_label"] = "Eligible" if eligible else "Not Eligible"
    patient["patient_id"] = f"P{str(patient_id).zfill(4)}"
    return patient

def generate_balanced_dataset(n_total=200):
    half = n_total // 2
    patients = []

    for i in range(half):
        patient = generate_patient(i + 1, eligible=True)
        patients.append(patient)

    i_offset = half + 1
    while len(patients) < n_total:
        patient = generate_patient(i_offset, eligible=False)
        # Just to be sure we aren't accidentally generating eligible patients
        if patient["eligibility_label"] == "Not Eligible":
            patients.append(patient)
            i_offset += 1

    random.shuffle(patients)
    return pd.DataFrame(patients)

# Generate and save
df = generate_balanced_dataset(200)
df.to_csv("balanced_varied_patients2.csv", index=False)

# Check distribution
print(df["eligibility_label"].value_counts())
print(df.head())
