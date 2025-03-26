import os
import re
import pandas as pd
import evaluate
import torch
from torch.utils.data import Dataset
from sklearn.model_selection import train_test_split
from transformers import (
    AutoTokenizer, AutoModelForSeq2SeqLM,
    Seq2SeqTrainer, Seq2SeqTrainingArguments
)

# ========== Metric ==========

accuracy_metric = evaluate.load("accuracy")
label2id = {
    "not eligible": 0,
    "eligible": 1,
    "eligible for some": 2,
    "eligible for most": 3
    }

id2label = {v: k for k, v in label2id.items()}
def build_compute_metrics(tokenizer):
    def compute_metrics(eval_pred):
        predictions, labels = eval_pred
        decoded_preds = tokenizer.batch_decode(predictions, skip_special_tokens=True)
        decoded_labels = tokenizer.batch_decode(labels, skip_special_tokens=True)

        decoded_preds = [p.strip().lower() for p in decoded_preds]
        decoded_labels = [l.strip().lower() for l in decoded_labels]

        # Convert to integers
        try:
            preds_ids = [label2id[p] for p in decoded_preds]
            labels_ids = [label2id[l] for l in decoded_labels]
        except KeyError as e:
            print(f"⚠️ Unknown label: {e}. Prediction: {decoded_preds}")
            return {"accuracy": 0.0}

        return accuracy_metric.compute(predictions=preds_ids, references=labels_ids)

    return compute_metrics

# ========== Field Formatter ==========

def format_patient_profile(patient: dict) -> str:
    return "\n".join([f"{k}: {v}" for k, v in patient.items()])

# ========== Trial Loader ==========

def read_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        return file.read()

def parse_document(document):
    key_value_pattern = re.compile(r'^([^,:]+):,(.*)$')
    section_pattern = re.compile(r'-{50,}')
    data = {}
    for line in document.split('\n'):
        if section_pattern.match(line):
            continue
        elif key_value_pattern.match(line):
            key, val = key_value_pattern.match(line).groups()
            data[key.strip()] = val.strip()
        elif line.strip() and list(data):
            last_key = list(data)[-1]
            data[last_key] += ' ' + line.strip()
    return data

def split_criteria(section):
    return [c.strip() for c in re.split(r'\.\s*', section) if c.strip()]

def process_trial_file(file_path):
    doc = read_file(file_path)
    data = parse_document(doc)
    eligibility = data.get("Eligibility Criteria", "")
    if "||" in eligibility:
        inc, exc = eligibility.split("||")
    else:
        inc, exc = eligibility, ""
    data["Inclusion Criteria"] = split_criteria(inc.replace("Inclusion:", "").strip())
    data["Exclusion Criteria"] = split_criteria(exc.replace("Exclusion:", "").strip())
    return data

def load_trials(folder_path):
    return [
        process_trial_file(os.path.join(folder_path, f))
        for f in os.listdir(folder_path)
        if f.endswith(".csv")
    ]

# ========== Dataset ==========

class TrialMatchingDataset(Dataset):
    def __init__(self, patient_df, trials, tokenizer, max_input_length=512, max_target_length=8):
        self.examples = []
        self.tokenizer = tokenizer
        self.max_input_length = max_input_length
        self.max_target_length = max_target_length

        for _, patient in patient_df.iterrows():
            profile_dict = patient.to_dict()
            patient_str = format_patient_profile(profile_dict)
            label = patient["eligibility_label"]

            for trial in trials:
                trial_name = trial.get("Name", "Unnamed Trial")
                inc = "\n- " + "\n- ".join(trial.get("Inclusion Criteria", [])[:6])
                exc = "\n- " + "\n- ".join(trial.get("Exclusion Criteria", [])[:6])
                input_text = f"""Patient Profile:
{patient_str}

Trial: {trial_name}
Inclusion Criteria:{inc}
Exclusion Criteria:{exc}
"""
                self.examples.append((input_text, label))

    def __len__(self):
        return len(self.examples)

    def __getitem__(self, idx):
        input_text, target_text = self.examples[idx]
        model_input = self.tokenizer(
            input_text,
            truncation=True,
            padding="max_length",
            max_length=self.max_input_length,
            return_tensors="pt"
        )
        label_input = self.tokenizer(
            target_text,
            truncation=True,
            padding="max_length",
            max_length=self.max_target_length,
            return_tensors="pt"
        )
        return {
            "input_ids": model_input["input_ids"].squeeze(),
            "attention_mask": model_input["attention_mask"].squeeze(),
            "labels": label_input["input_ids"].squeeze()
        }

# ========== Main Training ==========

def main():

    if torch.cuda.is_available():
        print(f"🔥 CUDA is available. Using GPU: {torch.cuda.get_device_name(0)}")
    else:
        print("⚠️ CUDA not available. Using CPU.")

    csv_path = "patients_data/testing_dataset.csv"
    trials_folder = "trials_data"
    model_name = "google/flan-t5-base"

    print("🔄 Loading tokenizer and model...")
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForSeq2SeqLM.from_pretrained(model_name)

    print("📋 Loading data...")
    full_df = pd.read_csv(csv_path)
    train_df, val_df = train_test_split(full_df, test_size=0.2, stratify=full_df["eligibility_label"], random_state=42)
    trials = load_trials(trials_folder)

    print("📚 Preparing datasets...")
    train_dataset = TrialMatchingDataset(train_df, trials, tokenizer)
    val_dataset = TrialMatchingDataset(val_df, trials, tokenizer)

    

    print("⚙️ Setting training arguments...")
    training_args = Seq2SeqTrainingArguments(
        output_dir="./t5_trial_matcher",
        per_device_train_batch_size=4,
        per_device_eval_batch_size=4,
        learning_rate=5e-5,
        num_train_epochs=3,
        evaluation_strategy="epoch",
        save_strategy="epoch",
        logging_dir="./logs",
        predict_with_generate=True,
        report_to="none"
    )

    print("🚀 Starting training...")
    trainer = Seq2SeqTrainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=val_dataset,
        tokenizer=tokenizer,
        compute_metrics=build_compute_metrics(tokenizer)
    )

    trainer.train()
    trainer.save_model("./t5_trial_matcher")
    print("✅ Model saved to ./t5_trial_matcher")

# ========== Entry Point ==========

if __name__ == "__main__":
    main()
