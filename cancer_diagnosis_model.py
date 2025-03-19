import pandas as pd
import random

# Load the dataset
df = pd.read_csv("updated_breast_cancer_patients.csv")

def generate_test_patient():
    
    patient = {
        "age": random.randint(df["age"].min(), df["age"].max()),
        "gender": random.choice(df["gender"].dropna().unique()),
        "cancer_type": random.choice(df["cancer_type"].dropna().unique()),
        "diagnosis_status": random.choice(df["diagnosis_status"].dropna().unique()),
        "tumor_characteristics": random.choice(df["tumor_characteristics"].dropna().unique()),
        "treatment_history": random.choice(df["treatment_history"].dropna().unique()),
        "genetic_mutations": random.choice(df["genetic_mutations"].dropna().unique()) if not df["genetic_mutations"].dropna().empty else "None",
        "ecog_performance_status": random.choice(df["ecog_performance_status"].dropna().unique()),
        "organ_function_status": random.choice(df["organ_function_status"].dropna().unique()),
        "presence_of_metastases": random.choice(df["presence_of_metastases"].dropna().unique()),
        "clinical_pathological_risk_features": random.choice(df["clinical_pathological_risk_features"].dropna().unique()),
        "comorbidities": random.choice(df["comorbidities"].dropna().unique()),
        "previous_cancer_history": random.choice(df["previous_cancer_history"].dropna().unique()),
        "pregnancy_breastfeeding_status": random.choice(df["pregnancy_breastfeeding_status"].dropna().unique()),
        "compliance_with_study_protocol": random.choice(df["compliance_with_study_protocol"].dropna().unique()),
    }
    
    # Print formatted output
    print("{")
    for key, value in patient.items():
        print(f'    "{key}": "{value}",')
    print("}")
    
    return patient

# Generate a test patient
new_test_patient = generate_test_patient()


def get_cancer_info(patient_profile):

    cancer_type = patient_profile.get("cancer_type", "Unknown")
    previous_cancer = patient_profile.get("previous_cancer_history", "No previous cancer")
    
    # Determine if previous cancer is the same as current
    same_cancer = previous_cancer.lower() == cancer_type.lower() if previous_cancer.lower() != "no previous cancer" else False
    
    return {
        "current_cancer": cancer_type,
        "previous_cancer": previous_cancer,
        "same_as_previous": same_cancer
    }

# Example usage

Classified = get_cancer_info(new_test_patient)
print(Classified)
