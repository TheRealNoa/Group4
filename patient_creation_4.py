import pandas as pd
import random
import os

# Natural-language labels for patient features
FEATURE_MAP = {
    "age_over_18": "Patient is over 18",
    "ecog_0_1": "ECOG performance status is 0 or 1",
    "adequate_organ_function": "Organ function is adequate",
    "received_radiotherapy": "Has received radiotherapy",
    "has_metastasis": "Has distant metastasis",
    "previous_cancer": "Has history of cancer",
    "cardiac_condition": "Has cardiac condition",
    "brca_mutation": "Has BRCA mutation",
    "prior_her2_treatment": "Has received HER2-targeted therapy before",
    "prior_endocrine_therapy": "Has received endocrine therapy before",
    "active_infection": "Has active infection",
    "pregnant_or_breastfeeding": "Is pregnant or breastfeeding",
    "lvef_below_50": "Left ventricular ejection fraction is below 50%",
    "arrhythmia": "Has arrhythmia",
    "ctla4_inhibitor": "Previously treated with CTLA-4 inhibitor",
    "cd137_agent": "Previously treated with CD137 agent",
    "ox40_agent": "Previously treated with OX40 agent",
    "topoisomerase_inhibitor": "Previously treated with topoisomerase inhibitor",
    "er_positive": "Estrogen receptor positive",
    "pr_positive": "Progesterone receptor positive",
    "her2_negative": "HER2 negative",
    "triple_negative": "Triple negative breast cancer",
    "smoker": "Smoker",
    "family_history": "Family history of cancer",
    "bmi_over_30": "BMI over 30"
}

# Random noise features
NOISE_KEYS = ["smoker", "family_history", "bmi_over_30"]

# Your TRIALS list goes here (unchanged)...

TRIALS = [
    {
        "name": "ASCENT-05",
        "inclusion": [
            "age_over_18", "ecog_0_1", "adequate_organ_function", "received_radiotherapy"
        ],
        "exclusion": [
            "has_metastasis", "previous_cancer", "cardiac_condition", "brca_mutation",
            "prior_her2_treatment", "prior_endocrine_therapy", "active_infection",
            "pregnant_or_breastfeeding", "lvef_below_50", "arrhythmia",
            "ctla4_inhibitor", "cd137_agent", "ox40_agent", "topoisomerase_inhibitor"
        ]
    },
    {
    "name": "CAMBRIA-2",
    "inclusion": [
        "age_over_18", "er_positive","her2_negative","early_stage_resected_breast_cancer",
        "has_metastatic_disease","completed_locoregional_therapy","neo_adjuvant_chemo_optional",
        "randomised_within_12_months_of_surgery","received_up_to_12_weeks_endocrine_therapy","ecog_0_1",
        "adequate_organ_function",
        "adequate_bone_marrow_function"
    ],
    "exclusion": [
        "has_locally_advanced_or_metastatic_breast_cancer","pathological_complete_response_to_neoadjuvant",
        "history_of_other_cancer","severe_or_uncontrolled_systemic_disease","lvef_below_50",
        "heart_failure_nyha_2_or_more","qtcf_over_480ms","concurrent_hormonal_therapy_non_cancer",
        "concurrent_anticancer_treatment_not_allowed","previous_camizestrant_or_similar_agents",
        "pregnant_or_breastfeeding","hypersensitivity_to_camizestrant","lhrh_intolerance_in_premenopausal"
    ]
    },
    {
    "name": "EMBER-4",
    "inclusion": [
        "age_over_18","er_positive","her2_negative","early_stage_resected_breast_cancer","has_distant_metastasis",
        "adjuvant_et_24_to_60_months","may_have_received_neo_adjuvant_chemo_or_targeted","increased_risk_of_recurrence",
        "ecog_0_1","adequate_organ_function"
    ],
    "exclusion": [
        "has_any_metastatic_disease","inflammatory_breast_cancer","et_gap_over_6_months","et_completed_more_than_6_months_ago",
        "history_of_breast_cancer_except_ipsilateral_dcis_5yrs_ago","pregnant_or_breastfeeding","planning_children_during_trial",
        "received_et_for_prevention","history_of_other_cancer","serious_medical_conditions_precluding_participation"
    ]
    },
    {
    "name": "EPIK-B5",
    "inclusion": [
        "age_over_18","signed_informed_consent","postmenopausal_female_only","er_or_pgr_positive","her2_negative",
        "measurable_lesion_recist_v1_1","progressed_on_ai_and_cdk46","max_two_prior_systemic_therapies_metastatic",
        "max_one_line_prior_chemo_metastatic","pik3ca_mutation_detected"
    ],
    "exclusion": [
        "symptomatic_visceral_disease_ineligible_for_et","relapse_over_12_months_post_endocrine_no_metastatic_treatment",
        "prior_fulvestrant_or_serds","prior_pi3k_mtor_or_akt_inhibitor"
    ]
    },
    {
    "name": "MK-2870-012",
    "inclusion": [
        "age_over_18","centrally_confirmed_tnbc","no_locoregional_or_distant_recurrence",
        "received_keynote_522_neoadjuvant_regimen","adequate_surgical_excision",
        "non_pathologic_complete_response","eligible_for_adjuvant_pembrolizumab",
        "randomisation_within_12_weeks_of_surgery","completed_adjuvant_radiation_if_indicated",
        "trop2_status_available_from_surgical_tissue","male_agrees_to_sperm_precautions",
        "female_not_pregnant_or_breastfeeding_and_using_contraception",
        "recovered_from_prior_therapy_aes","hiv_positive_controlled_on_art",
        "ecog_0_1","hbv_positive_on_treatment_and_undetectable"
    ],
    "exclusion": [
        "brca_mutation_eligible_for_olaparib","grade_over_2_peripheral_neuropathy",
        "severe_ocular_surface_disease","active_or_prior_ibd_or_chronic_diarrhea",
        "significant_cardiovascular_or_cerebrovascular_disease","prior_trop2_adc_or_topoisomerase_i_adc",
        "received_disallowed_adjuvant_anticancer_therapy","cyp3a4_inhibitor_or_inducer_not_discontinued",
        "prior_pd1_pdl1_ctla4_cd137_ox40_therapy","prior_systemic_therapy_within_4_weeks",
        "prior_radiation_within_3_weeks_or_radiation_steroids","received_live_vaccine_within_30_days",
        "recent_investigational_agent_or_device","active_additional_malignancy_last_5_years",
        "immunodeficiency_or_recent_immunosuppression","active_autoimmune_disease_last_2_years",
        "history_of_pneumonitis_or_current_ild","active_infection_requiring_systemic_therapy",
        "hiv_with_kaposi_or_castlemans","active_hbv_and_hcv_coinfection","history_of_organ_transplant"
    ]
    },
    {
    "name": "PREcoopERA",
    "inclusion": [
        "premenopausal_female","age_over_18", "no_hormonal_therapy_last_6_months",
        "histologically_confirmed_invasive_breast_cancer",
        "operable_stage_i_ii_iii_excluding_t4",
        "tumor_size_over_1cm",
        "multicentric_or_multifocal_allowed",
        "er_positive_asco_cap",
        "her2_negative_asco_cap",
        "ki67_over_10_percent",
        "ecog_0_1",
        "resting_hr_over_40bpm",
        "normal_hematologic_status",
        "normal_renal_function",
        "normal_liver_function",
        "inr_under_15_or_stable_on_anticoagulants",
        "negative_pregnancy_test_pre_randomization",
        "uses_contraception_during_treatment",
        "signed_informed_consent",
        "agrees_to_data_transfer_and_sample_submission"
    ],
    "exclusion": [
        "stage_iv_breast_cancer",
        "inflammatory_breast_cancer",
        "prior_treatment_for_current_cancer",
        "recent_gnrh_lhrh_analog_use",
        "major_surgery_within_4_weeks",
        "liver_disease_child_pugh_b_or_c",
        "severe_medical_or_psychiatric_conditions",
        "history_of_bleeding_disorders_or_thromboembolism",
        "active_or_historical_cardiac_disease",
        "lvef_below_50",
        "qtc_over_470ms_or_qt_related_syndromes",
        "abnormal_ecg_clinically_significant",
        "ventricular_dysrhythmia_risk",
        "qt_prolonging_medications",
        "cyp3a4_interactions_not_washout",
        "swallowing_difficulty",
        "active_ibd_or_gi_absorption_issues",
        "recent_serious_infection",
        "active_non_breast_malignancy",
        "pregnant_or_lactating",
        "any_condition_preventing_safe_participation",
        "likely_to_be_noncompliant",
        "contraindication_to_trial_drug",
        "recent_investigational_agent"
    ]
    },
    {
    "name": "TREAT ctDNA study",
    "inclusion": [
        "age_over_18",
        "er_positive_10_percent_or_more",
        "her2_negative_asco_cap",
        "elevated_recurrence_risk_post_treatment",
        "stage_iib_or_iii_with_adjuvant_chemo",
        "residual_disease_post_neoadjuvant_chemo",
        "pre_or_postmenopausal_female_allowed",
        "received_2_to_7_years_endocrine_therapy",
        "prior_adjuvant_cdk46_or_parp_allowed_if_12mo_ago",
        "multifocal_allowed_if_erpos_her2neg_all_foci",
        "ffpe_tumor_block_or_10_slides_available",
        "signed_informed_consent",
        "ctdna_positive_by_signatera_assay",
        "has_no_locoregional_or_metastatic_disease",
        "ecog_0_1",
        "adequate_organ_function",
        "negative_pregnancy_test"
    ],
    "exclusion": [
        "suspected_or_known_recurrent_disease",
        "prior_serd_or_er_antagonist",
        "history_of_invasive_breast_cancer",
        "other_malignancy_within_5_years_except_low_risk",
        "bilateral_breast_cancer",
        "active_participation_in_other_interventional_trial",
        "unresolved_grade_2_plus_toxicity_from_prior_therapy",
        "cannot_avoid_cyp3a4_interactions",
        "difficulty_tolerating_oral_medication",
        "cardiovascular_event_within_3_months",
        "child_pugh_b_or_c",
        "active_infection_grade_3_plus",
        "active_hbv_hcv_or_hiv_infection",
        "coagulopathy_or_thrombosis_last_6_months"
    ]
    },
    {
    "name": "UCARE",
    "inclusion": [
        "female_only",
        "age_over_18",
        "can_read_and_understand_english",
        "stage_i_to_iii_breast_cancer",
        "planned_for_systemic_chemotherapy"
    ],
    "exclusion": [
        "not_receiving_curative_chemotherapy",
        "unable_to_cooperate_with_protocol",
        "unable_to_give_informed_consent"
    ]
    },
    {
    "name": "Wavelia",
    "inclusion": [
        "female_only",
        "age_over_18",
        "signed_informed_consent",
        "breast_abnormality_over_1cm",
        "able_to_comply_with_protocol",
        "negative_pregnancy_test_day_of_procedure",
        "intact_breast_skin",
        "can_lie_prone_for_15_minutes",
        "biopsy_over_2_weeks_ago_if_applicable"
    ],
    "exclusion": [
        "cup_size_a_or_breast_too_small_for_mbi",
        "pregnant_or_breastfeeding",
        "breast_surgery_within_12_months",
        "active_or_metallic_implant_other_than_clip",
        "unsuitable_or_unlikely_to_comply_investigator_judgment"
    ]
}

    # Add more trials here as needed
]

def feature_to_text(key, value):
    label = FEATURE_MAP.get(key, key.replace("_", " ").capitalize())
    return f"{label}: {'Yes' if value else 'No'}"

def generate_patient(patient_id, trial, eligible=True):
    patient = {}

    inclusion_keys = trial["inclusion"]
    exclusion_keys = trial["exclusion"]
    violated_exclusions = []
    violated_inclusions = []

    # --- Inclusion fields ---
    for key in inclusion_keys:
        if eligible:
            value = random.choices([True, False], weights=[0.95, 0.05])[0]
            if not value:
                violated_inclusions.append(key)
        else:
            value = random.choice([True, False])
        patient[key] = value

    # --- Exclusion fields ---
    if eligible:
        for key in exclusion_keys:
            patient[key] = False
    else:
        for key in exclusion_keys:
            value = random.choices([True, False], weights=[0.3, 0.7])[0]
            patient[key] = value
            if value:
                violated_exclusions.append(key)
        if not violated_exclusions:
            key = random.choice(exclusion_keys)
            patient[key] = True
            violated_exclusions.append(key)

    # --- TNBC logic ---
    if eligible:
        patient["er_positive"] = False
        patient["pr_positive"] = False
        patient["her2_negative"] = True
        patient["triple_negative"] = True
    else:
        er = random.choice([True, False])
        pr = random.choice([True, False])
        her2 = random.choice([True, False])
        patient["er_positive"] = er
        patient["pr_positive"] = pr
        patient["her2_negative"] = her2
        patient["triple_negative"] = (not er and not pr and her2)

    # --- Noise fields ---
    for key in NOISE_KEYS:
        patient[key] = random.choice([True, False])

    # --- Natural-language profile ---
    nl_profile = [
        feature_to_text(k, v)
        for k, v in patient.items()
        if k in FEATURE_MAP
    ]
    patient_profile = "\n".join(nl_profile)

    # --- Explanation ---
    if eligible:
        if violated_inclusions:
            readable = [FEATURE_MAP.get(key, key.replace("_", " ").capitalize()) for key in violated_inclusions]
            explanation = f"Eligible despite minor inclusion gaps: {', '.join(readable)} set to No. No exclusion criteria violated."
        else:
            explanation = "Eligible: all required inclusion criteria mostly satisfied and no exclusion criteria violated."
    else:
        readable = [FEATURE_MAP.get(key, key.replace("_", " ").capitalize()) for key in violated_exclusions]
        explanation = f"Not eligible due to: {', '.join([f'{r} is Yes (violates exclusion)' for r in readable])}"

    # --- Final return (clean) ---
    return {
        "patient_id": f"{trial['name'][:4].upper()}_{str(patient_id).zfill(4)}",
        "trial_name": trial["name"],
        "eligibility_label": "Eligible" if eligible else "Not Eligible",
        "explanation": explanation,
        "natural_language_profile": patient_profile
    }


def generate_balanced_patients_for_trials(trials, patients_per_trial=500, output_dir="patients"):
    os.makedirs(output_dir, exist_ok=True)
    all_dfs = []

    for trial in trials:
        patients = []
        half = patients_per_trial // 2
        for i in range(half):
            patients.append(generate_patient(i + 1, trial, eligible=True))
        for i in range(half):
            patients.append(generate_patient(i + half + 1, trial, eligible=False))

        df = pd.DataFrame(patients)
        file_name = trial["name"].replace(" ", "_").replace("/", "_") + ".csv"
        file_path = os.path.join(output_dir, file_name)
        df.to_csv(file_path, index=False)
        print(f"✅ Saved {len(df)} patients for trial: {trial['name']} → {file_path}")
        all_dfs.append(df)

    return pd.concat(all_dfs, ignore_index=True)

# Run generation
df = generate_balanced_patients_for_trials(TRIALS, patients_per_trial=200)
df.to_csv("balanced.csv", index=False)
print(df["eligibility_label"].value_counts())
print(df["trial_name"].value_counts())
print(df[["patient_id", "trial_name", "eligibility_label", "explanation"]].head())
