
from flask import Flask, render_template, request, redirect, session, url_for
import os
import threading

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

@app.route("/scrape", methods=["POST"])
def scrape():
    if not session.get("logged_in"):
        return {"error": "Unauthorized"}, 401

    data = request.json
    cancer_type = data.get("cancer_type")
    country = data.get("country")

    print(f"🧪 Starting scrape: {cancer_type} in {country}")

    def run_scrape():
        scrape_trials(cancer_type, country)

    threading.Thread(target=run_scrape, daemon=True).start()
    return {"status": f"Scraping {cancer_type} trials in {country} started."}

if __name__ == "__main__":
    app.run(debug=True)
