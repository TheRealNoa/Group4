import pandas as pd
import random

TRIAL_FEATURES = [
    'age_over_18', 'triple_negative', 'er_positive', 'her2_negative', 'ecog_0_1',
    'adequate_organ_function', 'no_metastasis', 'previous_cancer',
    'received_radiotherapy', 'cardiac_condition', 'brca_mutation',
    'prior_her2_treatment', 'prior_endocrine_therapy', 'active_infection',
    'pregnant_or_breastfeeding', 'lvef_below_50', 'arrhythmia', 'ctla4_inhibitor',
    'cd137_agent', 'ox40_agent', 'topoisomerase_inhibitor'
]

TRIAL_RULES = [
    {
        'inclusion': ['age_over_18', 'triple_negative', 'her2_negative', 'ecog_0_1', 'adequate_organ_function'],
        'exclusion': ['no_metastasis', 'previous_cancer', 'prior_her2_treatment', 'brca_mutation']
    },
    {
        'inclusion': ['er_positive', 'adequate_organ_function', 'received_radiotherapy'],
        'exclusion': ['active_infection', 'arrhythmia', 'cardiac_condition']
    },
    {
        'inclusion': ['age_over_18', 'ecog_0_1'],
        'exclusion': ['ctla4_inhibitor', 'ox40_agent', 'topoisomerase_inhibitor']
    },
    {
        'inclusion': ['her2_negative', 'received_radiotherapy'],
        'exclusion': ['pregnant_or_breastfeeding', 'lvef_below_50']
    }
]

def generate_patient():
    patient = {}
    for feature in TRIAL_FEATURES:
        if feature in ['age_over_18', 'adequate_organ_function', 'no_metastasis']:
            patient[feature] = True
        else:
            patient[feature] = random.random() > 0.3
    return patient

def matches_trial(patient, trial):
    for inc in trial['inclusion']:
        if not patient.get(inc, False):
            return False
    for exc in trial['exclusion']:
        if patient.get(exc, False):  # exclusion violated
            return False
    return True

# Set total number of patients (must be divisible by 3 for equal split)
N = 30
target_per_label = N // 3

label_counts = {'Not Eligible': 0, 'Eligible for Some': 0, 'Eligible for Most': 0}
patients = []
patient_id = 1

while sum(label_counts.values()) < N:
    patient = generate_patient()
    matches = [matches_trial(patient, trial) for trial in TRIAL_RULES]
    matched_trials = sum(matches)

    if matched_trials == 0:
        label = 'Not Eligible'
    elif matched_trials < len(TRIAL_RULES) / 2:
        label = 'Eligible for Some'
    else:
        label = 'Eligible for Most'

    # Add only if we haven't reached the quota for this label
    if label_counts[label] < target_per_label:
        patient['eligibility_label'] = label
        patient['patient_id'] = f"P{patient_id:04d}"
        patients.append(patient)
        label_counts[label] += 1
        patient_id += 1

# Convert to DataFrame and export
final_df = pd.DataFrame(patients)
print(final_df['eligibility_label'].value_counts())
final_df.to_csv("patients_data/testing_dataset.csv", index=False)
