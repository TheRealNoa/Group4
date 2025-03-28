import pandas as pd
import random

# Define field groups
INCLUSION_KEYS = [
    "age_over_18", "ecog_0_1", "adequate_organ_function", "received_radiotherapy"
]

EXCLUSION_KEYS = [
    "no_metastasis",  # must be True
    "previous_cancer", "cardiac_condition", "brca_mutation",
    "prior_her2_treatment", "prior_endocrine_therapy",
    "active_infection", "pregnant_or_breastfeeding",
    "lvef_below_50", "arrhythmia", "ctla4_inhibitor",
    "cd137_agent", "ox40_agent", "topoisomerase_inhibitor"
]

# Optional/irrelevant features (used as noise)
NOISE_KEYS = ["smoker", "family_history", "bmi_over_30"]

def generate_patient(patient_id, eligible=True):
    patient = {}

    # --- TNBC logic ---
    if eligible:
        patient["er_positive"] = False
        patient["pr_positive"] = False
        patient["her2_negative"] = True
        patient["triple_negative"] = True
    else:
        # Introduce inconsistency or partial TNBC logic
        er = random.choice([True, False])
        pr = random.choice([True, False])
        her2 = random.choice([True, False])
        patient["er_positive"] = er
        patient["pr_positive"] = pr
        patient["her2_negative"] = her2
        patient["triple_negative"] = er is False and pr is False and her2 is True

    # --- Inclusion fields ---
    for key in INCLUSION_KEYS:
        patient[key] = True if eligible else random.choice([True, False])

    # --- Exclusion fields ---
    for key in EXCLUSION_KEYS:
        if eligible:
            patient[key] = False  # must be False to qualify
        else:
            # Add at least one violation
            patient[key] = random.choices([True, False], weights=[0.7, 0.3])[0]

    # --- Noise fields ---
    for key in NOISE_KEYS:
        patient[key] = random.choice([True, False])

    # Ensure one guaranteed violation if not eligible
    if not eligible:
        if random.random() < 0.5:
            # Flip an inclusion field
            key = random.choice(INCLUSION_KEYS)
            patient[key] = False
        else:
            # Flip an exclusion field to True
            key = random.choice(EXCLUSION_KEYS)
            patient[key] = True

    # Final fields
    patient["trial_name"] = "ASCENT-05"
    patient["eligibility_label"] = "Eligible" if eligible else "Not Eligible"
    patient["patient_id"] = f"P{str(patient_id).zfill(4)}"
    return patient

def generate_balanced_dataset(n_total=500):
    half = n_total // 2
    patients = []

    for i in range(half):
        patients.append(generate_patient(i + 1, eligible=True))

    i_offset = half + 1
    while len(patients) < n_total:
        patient = generate_patient(i_offset, eligible=False)
        patients.append(patient)
        i_offset += 1

    random.shuffle(patients)
    return pd.DataFrame(patients)

# Generate and save
df = generate_balanced_dataset(100)
df.to_csv("balanced_varied_patients2.csv", index=False)

# Check
print(df["eligibility_label"].value_counts())
print(df.head())
