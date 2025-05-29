import os
import pandas as pd

# Input and output paths
PATIENT_CSV = "patients.csv"
TRIALS_BASE_DIR = "trials_data"
OUTPUT_CSV = "patients_with_trials.csv"

# Mapping between patient cancer types and folder names
CANCER_TYPE_MAP = {
    "breast": "breast",
    "lung": "lung",
    "myeloma": "multiple_myeloma",
    "prostate": "genitourinary",
    "cll": "cll"  # You may need to normalize this in your patient CSV
}

# Function to extract trial names from CSV files in a folder
def get_trial_names_for_type(cancer_type_folder):
    trial_names = []
    folder_path = os.path.join(TRIALS_BASE_DIR, cancer_type_folder)
    if not os.path.isdir(folder_path):
        return trial_names

    for filename in os.listdir(folder_path):
        if filename.endswith(".csv"):
            filepath = os.path.join(folder_path, filename)
            try:
                df = pd.read_csv(filepath, header=None)
                for i in range(len(df)):
                    row = df.iloc[i]
                    if "Name:" in row[0]:
                        trial_names.append(row[1])
                        break
            except Exception as e:
                print(f"Error reading {filename}: {e}")

    return trial_names

# Load patient data
df_patients = pd.read_csv(PATIENT_CSV)

# Process each patient
trial_list_column = []
for _, row in df_patients.iterrows():
    cancer_type = row["Cancer type"].strip().lower()
    mapped_type = CANCER_TYPE_MAP.get(cancer_type, None)

    if mapped_type:
        trial_names = get_trial_names_for_type(mapped_type)
        trial_list = "; ".join(trial_names) if trial_names else "No open trials"
    else:
        trial_list = "Cancer type not recognized"

    trial_list_column.append(trial_list)

# Update patient DataFrame
df_patients["Clinical trial open for enrollment"] = trial_list_column

# Save the updated CSV
df_patients.to_csv(OUTPUT_CSV, index=False)
print(f"✅ Updated patient records saved to: {OUTPUT_CSV}")
