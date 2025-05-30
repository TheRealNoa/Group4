import os
import pandas as pd

# Input and output paths
PATIENT_CSV = "patients.csv"
TRIALS_BASE_DIR = "trials_data"
OUTPUT_CSV = "patients_with_trials.csv"

# Normalize cancer type folder mapping
CANCER_TYPE_MAP = {
    "breast": "breast",
    "lung": "lung",
    "myeloma": "multiple_myeloma",
    "prostate": "genitourinary",
    "cll": "cll"
}

def normalize_country(name):
    return name.strip().lower().replace(" ", "_")

def normalize_cancer_type(name):
    return CANCER_TYPE_MAP.get(name.strip().lower(), None)

# Function to extract trial names from a specific country + cancer type folder
def get_trial_names_for_patient(country, cancer_type_folder):
    trial_names = []
    folder_path = os.path.join(TRIALS_BASE_DIR, normalize_country(country), cancer_type_folder)
    
    if not os.path.isdir(folder_path):
        return trial_names

    for filename in os.listdir(folder_path):
        if filename.endswith(".csv"):
            filepath = os.path.join(folder_path, filename)
            try:
                df = pd.read_csv(filepath, header=None)
                for i in range(len(df)):
                    row = df.iloc[i]
                    if "Name:" in str(row[0]):
                        trial_names.append(str(row[1]))
                        break
            except Exception as e:
                print(f"Error reading {filepath}: {e}")

    return trial_names

# Load patient data
df_patients = pd.read_csv(PATIENT_CSV)

# Build trial list column
trial_list_column = []
for _, row in df_patients.iterrows():
    country = row["Country"]
    cancer_type = row["Cancer type"]

    cancer_type_folder = normalize_cancer_type(cancer_type)
    if not cancer_type_folder:
        trial_list_column.append("Cancer type not recognized")
        continue

    trial_names = get_trial_names_for_patient(country, cancer_type_folder)
    trial_list = "; ".join(trial_names) if trial_names else "No open trials"
    trial_list_column.append(trial_list)

# Update and save patient file
df_patients["Clinical trial open for enrollment"] = trial_list_column
df_patients.to_csv(OUTPUT_CSV, index=False)
print(f"✅ Updated patient records saved to: {OUTPUT_CSV}")
