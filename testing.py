import pandas as pd

def format_patient_profile(row):
    """
    Converts a patient's feature row (e.g., from a pandas DataFrame) 
    into a readable string for model input.
    """
    field_descriptions = {
        "age_over_18": "Age over 18",
        "triple_negative": "Triple negative breast cancer",
        "er_positive": "Estrogen receptor positive",
        "her2_negative": "HER2 negative",
        "ecog_0_1": "ECOG performance status 0 or 1",
        "adequate_organ_function": "Adequate organ function",
        "no_metastasis": "No metastasis",
        "previous_cancer": "History of previous cancer",
        "received_radiotherapy": "Received radiotherapy",
        "cardiac_condition": "Cardiac condition",
        "brca_mutation": "BRCA gene mutation",
        "prior_her2_treatment": "Prior HER2 treatment",
        "prior_endocrine_therapy": "Prior endocrine therapy",
        "active_infection": "Has active infection",
        "pregnant_or_breastfeeding": "Pregnant or breastfeeding",
        "lvef_below_50": "LVEF below 50%",
        "arrhythmia": "Cardiac arrhythmia",
        "ctla4_inhibitor": "Treated with CTLA-4 inhibitor",
        "cd137_agent": "Treated with CD137 agent",
        "ox40_agent": "Treated with OX40 agent",
        "topoisomerase_inhibitor": "Treated with topoisomerase inhibitor",
    }

    lines = []
    for field, description in field_descriptions.items():
        value = row[field]
        status = "Yes" if value else "No"
        lines.append(f"{description}: {status}")

    return "\n".join(lines)

def main():

    df = pd.read_csv("patients_data/testing_dataset2.csv")
    patient_row = df.iloc[0]

    formatted_input = format_patient_profile(patient_row)
    print(formatted_input)
if __name__ == "__main__":
    main()