
from flask import Flask, render_template, request, redirect, session, url_for
import os
import csv
import threading
from flask import Flask, request, jsonify

from scraper import scrape_trials

app = Flask(__name__)
app.secret_key = os.urandom(24)

@app.route("/", methods=["GET"])
def root():
    if session.get("logged_in"):
        return redirect(url_for("home"))
    return redirect(url_for("login"))

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        if email and email.endswith("@hse.ie"):
            session["logged_in"] = True
            session["email"] = email
            return redirect(url_for("home"))
        else:
            return render_template("login.html", error="Only @hse.ie emails are allowed.")
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

def format_trials_for_web(trial_directory):
    trials_output = []
    for root, _, files in os.walk(trial_directory):
        for file in files:
            if file.endswith(".csv"):
                filepath = os.path.join(root, file)
                try:
                    with open(filepath, encoding="utf-8") as f:
                        reader = csv.reader(f)
                        name = "Unnamed Trial"
                        eligibility = "Eligibility not found"
                        for row in reader:
                            if row and row[0].startswith("Name:"):
                                name = row[1] if len(row) > 1 else name
                            elif row and any("Eligibility Criteria" in cell for cell in row):
                                if len(row) > 1:
                                    # most common format
                                    eligibility = row[1]
                                elif "Eligibility Criteria:" in row[0]:
                                    # fallback: single cell with embedded text
                                    eligibility = row[0].split("Eligibility Criteria:")[-1].strip()
                        trials_output.append({"name": name, "eligibility": eligibility})
                except Exception as e:
                    print(f"❌ Error reading {filepath}: {e}")
    return trials_output

@app.route("/scrape", methods=["POST"])
def scrape_route():
    data = request.get_json()
    cancer_type = data.get("cancer_type")
    country = data.get("country", "Ireland")

    # Run the scraper
    scrape_trials(cancer_type, country)

    # Define directory where results were saved
    trial_dir = os.path.join("trials_data", country.lower().replace(" ", "_"), cancer_type.lower().replace(" ", "_"))

    # Format results
    trials_data = format_trials_for_web(trial_dir)
    return jsonify({"trials": trials_data})
if __name__ == "__main__":
    app.run(debug=True)
