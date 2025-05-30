# app.py

from flask import Flask, render_template, request, redirect, session, url_for, jsonify
import os
import csv
from scraper import scrape_trials

app = Flask(__name__)
app.secret_key = os.urandom(24)

@app.route("/")
def root():
    return redirect(url_for("home" if session.get("logged_in") else "login"))

@app.route("/login", methods=["GET", "POST"])

def login():
    def is_valid_patient_id(email):
        if not email.endswith("@hse.ie"):
            return False
        patient_id = email.split("@")[0]
        try:
            with open("patients.csv", newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                return any(row["Patient ID"] == patient_id for row in reader)
        except Exception as e:
            print(f"Error reading patients.csv: {e}")
            return False

    if request.method == "POST":
        email = request.form.get("email")
        if email and is_valid_patient_id(email):
            session.update({"logged_in": True, "email": email})
            return redirect(url_for("home"))
        return render_template("login.html", error="Invalid Patient ID or email format. Use PatientID@hse.ie")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/home")
def home():
    if not session.get("logged_in"):
        return redirect(url_for("login"))
    return render_template("index.html")

@app.route("/scrape", methods=["POST"])
def scrape_route():
    data = request.get_json()
    cancer_type = data.get("cancer_type")
    country = data.get("country", "Ireland")

    # Run the scraper ONCE
    filepaths = scrape_trials(cancer_type, country)

    def format_trials_from_paths(paths):
        trials_output = []
        for path in paths:
            try:
                with open(path, encoding="utf-8") as f:
                    reader = csv.reader(f)
                    name = "Unnamed Trial"
                    eligibility = "Eligibility not found"
                    for row in reader:
                        if row and row[0].startswith("Name:"):
                            name = row[1]
                        elif row and any("Eligibility Criteria" in cell for cell in row):
                            eligibility = row[1] if len(row) > 1 else row[0].split("Eligibility Criteria:")[-1].strip()
                    trials_output.append({"name": name, "eligibility": eligibility})
            except Exception as e:
                print(f"❌ Error reading {path}: {e}")
        return trials_output

    return jsonify({"trials": format_trials_from_paths(filepaths)})

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)
