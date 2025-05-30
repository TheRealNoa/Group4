import pandas as pd
import random
import os
import matplotlib.pyplot as plt

# Parameters
NUM_PATIENTS = 500
OUTPUT_FILE = "patients.csv"

# Fixed values
CANCER_TYPES = ["breast", "lung", "CLL", "myeloma", "prostate"]
DIAGNOSIS_TYPES = ["newly_diagnosed", "relapsed"]
EU_COUNTRIES = [
    "Ireland", "Austria", "Belgium", "Bulgaria", "Croatia", "Cyprus", "Czech Republic",
    "Denmark", "Estonia", "Finland", "France", "Germany", "Greece", "Hungary", "Italy",
    "Latvia", "Lithuania", "Luxembourg", "Malta", "Netherlands", "Poland", "Portugal",
    "Romania", "Slovakia", "Slovenia", "Spain", "Sweden"
]
COUNTIES = [
    "Carlow", "Cavan", "Clare", "Cork", "Donegal", "Dublin", "Galway", "Kerry",
    "Kildare", "Kilkenny", "Laois", "Leitrim", "Limerick", "Longford", "Louth",
    "Mayo", "Meath", "Monaghan", "Offaly", "Roscommon", "Sligo", "Tipperary",
    "Waterford", "Westmeath", "Wexford", "Wicklow"
]

FIRST_NAMES = ["Alice", "Bob", "Charlie", "Diana", "Ethan", "Fiona", "George", "Hannah"]
LAST_NAMES = ["Smith", "Johnson", "Brown", "Taylor", "Anderson", "Lee", "Martin", "Clark"]

AGE_GROUPS = [
    range(7, 18),     
    range(18, 29),    
    range(29, 39),    
    range(39, 49),    
    range(49, 59),    
    range(59, 69),    
    range(69, 79),    
    range(79, 91)     
]

#Actual generation code
def generate_patients(num_patients, output_file):
    patients = []
    num_age_groups = len(AGE_GROUPS)
    num_cancer_types = len(CANCER_TYPES)
    group_size = num_patients // (num_age_groups * num_cancer_types)

    patient_id = 1
    for age_group in AGE_GROUPS:
        for cancer_type in CANCER_TYPES:
            for _ in range(group_size):
                name = f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"
                age = random.choice(age_group)  
                diagnosis_type = random.choice(DIAGNOSIS_TYPES)
                trial_open = random.choice(["Yes", "No"])
                country = random.choice(EU_COUNTRIES)
                county = random.choice(COUNTIES)

                patients.append({
                    "Patient name": name,
                    "Patient age": age,
                    "Diagnosis type": diagnosis_type,
                    "Cancer type": cancer_type,
                    "Clinical trial open for enrollment": trial_open,
                    "Country": country,
                    "County": county
                })
                patient_id += 1

    df = pd.DataFrame(patients)
    df.to_csv(output_file, index=False)


# Run it
generate_patients(NUM_PATIENTS, OUTPUT_FILE)

# Data visualisation
df = pd.read_csv(OUTPUT_FILE)

bins = [6, 17, 28, 38, 48, 58, 68, 78, 90]
labels = ["7–17", "18–28", "29–38", "39–48", "49–58", "59–68", "69–78", "79–90"]

df["Age Group"] = pd.cut(df["Patient age"], bins=bins, labels=labels, right=True, include_lowest=True)

grouped = df.groupby(["Age Group", "Cancer type"]).size().unstack(fill_value=0)

ax = grouped.plot(kind="bar", figsize=(12, 6))
plt.title("Cancer Type Distribution by Age Group")
plt.xlabel("Age Group")
plt.ylabel("Number of Patients")
plt.xticks(rotation=45)
plt.grid(axis='y')

plt.legend(title="Cancer Type", bbox_to_anchor=(1.05, 1), loc='upper left')
plt.tight_layout()
plt.show()
