from flask import Flask, render_template, request, redirect, session, url_for, jsonify, send_file
import os
import csv
import pyotp
from scraper import scrape_trials
from io import BytesIO
import qrcode

app = Flask(__name__)

app.secret_key = 'your-secret-key'

ADMIN_SECRETS_FILE = "admin_secrets.csv"

def load_admin_emails():
    try:
        with open(ADMIN_SECRETS_FILE, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            return set(row["email"].lower() for row in reader)
    except FileNotFoundError:
        return {"admin@hse.ie"}  # fallback default if file is missing

ADMIN_EMAILS = load_admin_emails()

def load_admin_secrets():
    secrets = {}
    try:
        with open(ADMIN_SECRETS_FILE, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                secrets[row["email"]] = {
                    "secret": row["secret"],
                    "qr_shown": row.get("qr_shown", "false").lower() == "true"
                }
    except FileNotFoundError:
        pass
    return secrets


def save_admin_secrets(secrets):
    with open(ADMIN_SECRETS_FILE, "w", newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=["email", "secret", "qr_shown"])
        writer.writeheader()
        for email, data in secrets.items():
            writer.writerow({
                "email": email,
                "secret": data["secret"],
                "qr_shown": str(data.get("qr_shown", False)).lower()
            })


def get_or_create_secret(email):
    secrets = load_admin_secrets()
    if email not in secrets:
        secrets[email] = {
            "secret": pyotp.random_base32(),
            "qr_shown": False
        }
        save_admin_secrets(secrets)
    return secrets[email]["secret"]


def mark_qr_as_shown(email):
    secrets = load_admin_secrets()
    if email in secrets:
        secrets[email]["qr_shown"] = True
        save_admin_secrets(secrets)


def reset_admin_2fa(email):
    secrets = load_admin_secrets()
    secrets[email] = {
        "secret": pyotp.random_base32(),
        "qr_shown": False
    }
    save_admin_secrets(secrets)


def remove_admin(email):
    secrets = load_admin_secrets()
    if email in secrets:
        del secrets[email]
    save_admin_secrets(secrets)
    ADMIN_EMAILS.discard(email)


@app.route("/")
def root():
    return redirect(url_for("home" if session.get("logged_in") else "login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    def is_valid_patient_id(email):
        if email.lower() in ADMIN_EMAILS:
            return True
        if not email.endswith("@hse.ie"):
            return False
        patient_id = email.split("@")[0]
        try:
            with open("patients.csv", newline='', encoding="utf-8") as f:
                reader = csv.DictReader(f)
                return any(row["Patient ID"] == patient_id for row in reader)
        except:
            return False

    if request.method == "POST":
        email = request.form.get("email")
        if email and is_valid_patient_id(email):
            session.update({"logged_in": True, "email": email})
            return redirect(url_for("home"))
        return render_template("login.html", error="Invalid Patient ID or email format.")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/home")
def home():
    if not session.get("logged_in"):
        return redirect(url_for("login"))

    email = session["email"]
    is_admin = email in ADMIN_EMAILS
    is_verified = session.get("admin_verified", False)
    patient_id = email.split("@")[0]
    patient_info = {}

    try:
        with open("patients.csv", newline='', encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row["Patient ID"] == patient_id:
                    patient_info = row
    except:
        pass

    return render_template("index.html", patient_info=patient_info, is_admin=is_admin, admin_verified=is_verified)


@app.route("/admin_qr")
def admin_qr():
    email = session.get("email")
    if email not in ADMIN_EMAILS:
        return "Unauthorized", 403

    secret = get_or_create_secret(email)
    uri = pyotp.TOTP(secret).provisioning_uri(name=email, issuer_name="CancerTrialsScraper")
    img = qrcode.make(uri)
    buf = BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    return send_file(buf, mimetype='image/png')


@app.route("/admin_qr_shown", methods=["POST"])
def admin_qr_shown():
    email = session.get("email")
    if email in ADMIN_EMAILS:
        mark_qr_as_shown(email)
        return jsonify({"success": True})
    return jsonify({"error": "Unauthorized"}), 403


@app.route("/verify_2fa", methods=["POST"])
def verify_2fa():
    email = session.get("email")
    if email not in ADMIN_EMAILS:
        return jsonify({"success": False, "error": "Unauthorized"}), 403

    data = request.get_json()
    code = data.get("code", "")
    secrets = load_admin_secrets()

    if email not in secrets:
        return jsonify({"success": False, "error": "2FA setup not complete"}), 403

    totp = pyotp.TOTP(secrets[email]["secret"])
    if totp.verify(code):
        session["admin_verified"] = True  # ✅ Set the flag
        return jsonify({"success": True, "qr_shown": True})
    return jsonify({"success": False, "error": "Invalid 2FA code"})

@app.route("/add_admin", methods=["POST"])
def add_admin():
    email = session.get("email")
    if email not in ADMIN_EMAILS:
        return jsonify({"success": False, "error": "Unauthorized"}), 403

    data = request.get_json()
    new_email = data.get("email", "").strip().lower()
    if not new_email.endswith("@hse.ie") or new_email in ADMIN_EMAILS:
        return jsonify({"success": False, "error": "Invalid or duplicate email"})

    ADMIN_EMAILS.add(new_email)
    get_or_create_secret(new_email)
    return jsonify({"success": True, "admins": list(ADMIN_EMAILS)})


@app.route("/admin_list")
def admin_list():
    email = session.get("email")
    if email not in ADMIN_EMAILS:
        return jsonify({"error": "Unauthorized"}), 403
    return jsonify({"admins": list(ADMIN_EMAILS)})


@app.route("/manage_admin", methods=["POST"])
def manage_admin():
    email = session.get("email")
    if email not in ADMIN_EMAILS:
        return jsonify({"success": False, "error": "Unauthorized"}), 403

    data = request.get_json()
    target_email = data.get("target_email")
    action = data.get("action")

    if target_email not in ADMIN_EMAILS:
        return jsonify({"success": False, "error": "Target not an admin"})

    if action == "remove":
        remove_admin(target_email)
        return jsonify({"success": True, "message": "Admin removed"})

    if action == "reset_2fa":
        reset_admin_2fa(target_email)
        return jsonify({"success": True, "message": "2FA reset"})

    return jsonify({"success": False, "error": "Unknown action"})


@app.route("/admin_status")
def admin_status():
    email = session.get("email")
    if email not in ADMIN_EMAILS:
        return jsonify({"error": "Unauthorized"}), 403

    secrets = load_admin_secrets()
    qr_shown = secrets.get(email, {}).get("qr_shown", False)
    return jsonify({ "qr_shown": qr_shown })

@app.route("/admin")
def admin_entry():
    email = session.get("email")
    if not session.get("logged_in"):
        return redirect(url_for("login"))

    is_admin = email in ADMIN_EMAILS
    if not is_admin:
        return "You are not authorized to view this page.", 403

    return render_template("admin_login.html", is_admin=True)

@app.route("/admin_panel")
def admin_panel():
    email = session.get("email")
    if email not in ADMIN_EMAILS or not session.get("admin_verified"):
        return redirect(url_for("admin_entry")) 
    return render_template("admin_panel.html", is_admin=True)

@app.route("/scrape", methods=["POST"])
def scrape_route():
    data = request.get_json()
    cancer_type = data.get("cancer_type")
    country = data.get("country", "Ireland")
    filepaths = scrape_trials(cancer_type, country)

    def format_trials_from_paths(paths):
        trials_output = []
        for path in paths:
            try:
                with open(path, encoding="utf-8") as f:
                    reader = csv.reader(f)
                    trial = {"name": "Unnamed Trial", "eligibility": "N/A", "link": "#"}
                    for row in reader:
                        if row and row[0].startswith("Name:"):
                            trial["name"] = row[1]
                        elif row and row[0].startswith("More Detailed Information:"):
                            trial["link"] = row[1]
                        elif row and "Eligibility Criteria" in row[0]:
                            trial["eligibility"] = row[1] if len(row) > 1 else row[0].split(":")[-1]
                    trials_output.append(trial)
            except:
                pass
        return trials_output

    return jsonify({"trials": format_trials_from_paths(filepaths)})


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)
