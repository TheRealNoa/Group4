import pandas as pd
import random
import os
import matplotlib.pyplot as plt 

# Parameters
NUM_PATIENTS = 100
OUTPUT_FILE = "patients.csv"

# Fixed values
CANCER_TYPES = ["breast", "lung", "CLL", "myeloma", "prostate"]
DIAGNOSIS_TYPES = ["newly diagnosed", "relapsed"]
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

EXCLUSIVE_STATUSES = [
    ["Newly diagnosed", "Relapsed", "Treatment completed"],  # Diagnosis status
    ["Stable", "Unstable", "Deteriorating", "Improving", "Critical", "Terminal"],  # Overall condition
    ["Ambulatory", "Bedbound", "Wheelchair dependent", "Needs assistance with ADLs", "Independent"],  # Functional status
]
OTHER_STATUSES = [
    "On active treatment","Palliative care only","Follow-up for surveillance","Pain uncontrolled",
    "Symptomatic","Asymptomatic","Needs urgent intervention","For second opinion"]

DISEASE_GROUPS = ["Solid Tumor", "Hematological Malignancy", "Sarcoma", "CNS Tumor"]

T_STAGE = ["T0", "T1", "T2", "T3", "T4"]

N_STAGE = ["N0", "N1", "N2", "N3"]

M_STAGE = ["M0", "M1"]

GRADES = ["Well differentiated", "Moderately differentiated", "Poorly differentiated", "Undifferentiated"]

HISTOLOGIES = ["Adenocarcinoma", "Squamous cell carcinoma", "Small cell carcinoma", "Lymphoma", "Sarcoma"]

MUTATIONS = ["None", "EGFR", "KRAS", "BRAF", "TP53", "ALK", "BRCA1", "BRCA2"]

TREATMENTS = ["None", "Surgery", "Chemotherapy", "Radiotherapy", "Immunotherapy", "Targeted therapy"]

GENDER = ["Male","Female"]

this_year = 2025

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

# For generating patient IDs
def generate_six_digit_id(base_id):
    remaining_digits = 6 - len(str(base_id))
    suffix = ''.join(random.choices('0123456789', k=remaining_digits))
    return f"{base_id}{suffix}"

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
                year_of_birth = this_year - age
                diagnosis_type = random.choice(DIAGNOSIS_TYPES)
                trial_open = random.choice(["Yes", "No"])
                country = random.choice(EU_COUNTRIES)
                county = random.choice(COUNTIES) if country == "Ireland" else None
                ECOG = random.randint(0, 5)

                # Patient status on referral (non-conflicting)
                status_pool = []
                exclusive_statuses = [list(group) for group in EXCLUSIVE_STATUSES]
                
                if diagnosis_type == "newly_diagnosed":
                    if "Relapsed" in exclusive_statuses[0]:
                        exclusive_statuses[0].remove("Relapsed")
                elif diagnosis_type == "relapsed":
                    if "Newly diagnosed" in exclusive_statuses[0]:
                        exclusive_statuses[0].remove("Newly diagnosed")
                for group in exclusive_statuses:
                    status_pool.append(random.choice(group))
                status_pool.extend(OTHER_STATUSES)
                num_statuses = random.randint(1, 3)
                final_statuses = random.sample(status_pool, num_statuses)
                status_on_referral = ", ".join(final_statuses)

                # Disease characteristics
                disease_group = random.choice(DISEASE_GROUPS)
                t_stage = random.choice(T_STAGE)
                n_stage = random.choice(N_STAGE)
                m_stage = random.choice(M_STAGE)
                grade = random.choice(GRADES)
                histology = random.choice(HISTOLOGIES)
                gender = random.choice(GENDER)
                # Mutations detected: if 'None', then only 'None'
                if random.random() < 0.3:
                    mutations_detected = "None"
                else:
                    possible_mutations = [m for m in MUTATIONS if m != "None"]
                    num_mutations = random.randint(1, 2)
                    mutations = random.sample(possible_mutations, num_mutations)
                    mutations_detected = ", ".join(mutations)

                # Previous treatment logic
                TREATMENT_OPTIONS = ["Surgery", "Chemotherapy", "Radiotherapy", "Immunotherapy", "Targeted therapy"]
                prob = random.random()
                if prob < 0.2:
                    # 20% chance: No treatment
                    previous_treatment = "None"
                    more_than_one_treatment = "No"
                elif prob < 0.7:
                    # 50% chance: One treatment
                    previous_treatment = random.choice(TREATMENT_OPTIONS)
                    more_than_one_treatment = "No"
                else:
                    # 30% chance: Multiple treatments
                    num_treatments = random.randint(2, min(3, len(TREATMENT_OPTIONS)))
                    treatments = random.sample(TREATMENT_OPTIONS, num_treatments)
                    previous_treatment = ", ".join(treatments)
                    more_than_one_treatment = "Yes"

            
                patients.append({
                    "Patient ID": generate_six_digit_id(patient_id),
                    "Patient name": name,
                    "Year of birth": year_of_birth, #update
                    "ECOG": ECOG,
                    "Gender": gender,
                    "Diagnosis type": diagnosis_type,
                    "Patient status on referral": status_on_referral,
                    "Disease group": disease_group,
                    "T stage": t_stage,
                    "N stage": n_stage,
                    "M stage": m_stage,
                    "Grade": grade,
                    "Histology": histology,
                    "Mutations detected": mutations_detected,
                    "Previous treatment": previous_treatment if more_than_one_treatment == "No" else "See 'More than 1 treatment'",
                    "More than 1 treatment": previous_treatment if more_than_one_treatment == "Yes" else "No",
                    "Cancer type": cancer_type,
                    #"Clinical trial open for enrollment": trial_open,
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

df["Age Group"] = pd.cut(df["Year of birth"], bins=bins, labels=labels, right=True, include_lowest=True)

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

