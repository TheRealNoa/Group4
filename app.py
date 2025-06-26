from flask import Flask, render_template, request, redirect, session, url_for, jsonify, send_file, abort
import os
import json
import pyotp
from scraper import scrape_trials
from matcher import run_screening
from io import BytesIO
import qrcode
import csv
from functools import wraps
app = Flask(__name__)

app.secret_key = 'your-secret-key'

ADMIN_SECRETS_FILE = "admin_secrets.json"


def require_permission(permission_name):
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            email = session.get("email")
            if email not in ADMIN_EMAILS:
                return jsonify({"success": False, "error": "Unauthorized"}), 403

            secrets = load_admin_secrets()
            perms = secrets.get(email, {}).get("permissions", [])

            if permission_name not in perms:
                return jsonify({"success": False, "error": "No permission to do this action"}), 403

            return f(*args, **kwargs)
        return wrapped
    return decorator


def load_admin_secrets():
    if not os.path.exists(ADMIN_SECRETS_FILE):
        return {}
    with open(ADMIN_SECRETS_FILE, encoding='utf-8') as f:
        return json.load(f)


def save_admin_secrets(secrets):
    with open(ADMIN_SECRETS_FILE, "w", encoding='utf-8') as f:
        json.dump(secrets, f, indent=2)


def load_admin_emails():
    return set(load_admin_secrets().keys())


ADMIN_EMAILS = load_admin_emails()


def get_or_create_secret(email):
    secrets = load_admin_secrets()
    if email not in secrets:
        secrets[email] = {
            "secret": pyotp.random_base32(),
            "qr_shown": False,
            "permissions": ["add_admin", "remove_admin", "reset_2fa"] # These are default permissions.
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
        "qr_shown": False,
        "permissions": ["add_admin", "remove_admin", "reset_2fa"]
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
        session["admin_verified"] = True
        mark_qr_as_shown(email)
        return jsonify({"success": True})
    return jsonify({"success": False, "error": "Invalid 2FA code"})


@app.route("/add_admin", methods=["POST"])
@require_permission("add_admin")
def add_admin():
    data = request.get_json()
    new_email = data.get("email", "").strip().lower()
    if not new_email.endswith("@hse.ie") or new_email in ADMIN_EMAILS:
        return jsonify({"success": False, "error": "Invalid or duplicate email"})

    ADMIN_EMAILS.add(new_email)
    get_or_create_secret(new_email)
    return jsonify({"success": True, "admins": list(ADMIN_EMAILS)})


@app.route("/remove_admin", methods=["POST"])
@require_permission("remove_admin")
def remove_admin_route():
    data = request.get_json()
    target_email = data.get("target_email")

    if target_email not in ADMIN_EMAILS:
        return jsonify({"success": False, "error": "Target not an admin"})

    remove_admin(target_email)
    return jsonify({"success": True, "message": "Admin removed"})


@app.route("/reset_2fa", methods=["POST"])
@require_permission("reset_2fa")
def reset_2fa_route():
    data = request.get_json()
    target_email = data.get("target_email")

    if target_email not in ADMIN_EMAILS:
        return jsonify({"success": False, "error": "Target not an admin"})

    reset_admin_2fa(target_email)
    return jsonify({"success": True, "message": "2FA reset"})


@app.route("/admin_list")
def admin_list():
    email = session.get("email")
    if email not in ADMIN_EMAILS:
        return jsonify({"error": "Unauthorized"}), 403
    return jsonify({"admins": list(ADMIN_EMAILS)})


@app.route("/admin_status")
def admin_status():
    email = session.get("email")
    if email not in ADMIN_EMAILS:
        return jsonify({"error": "Unauthorized"}), 403

    secrets = load_admin_secrets()
    qr_shown = secrets.get(email, {}).get("qr_shown", False)
    return jsonify({"qr_shown": qr_shown})


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


@app.route("/admin_permissions")
@require_permission("see_permissions")
def admin_permissions():
    email = request.args.get("email", "").lower()
    all_admins = load_admin_secrets()
    if email not in all_admins:
        return jsonify({"error": "Admin not found"}), 404
    return jsonify({"permissions": all_admins[email].get("permissions", [])})


@app.route("/set_permissions", methods=["POST"])
def set_permissions():
    if session.get("email") not in ADMIN_EMAILS:
        return jsonify({"success": False, "error": "Unauthorized"}), 403

    data = request.get_json()
    target_email = data.get("email", "").lower()
    permissions = data.get("permissions", [])

    secrets = load_admin_secrets()
    if target_email not in secrets:
        return jsonify({"success": False, "error": "Target admin not found"}), 404

    secrets[target_email]["permissions"] = permissions
    save_admin_secrets(secrets)
    return jsonify({"success": True, "message": "Permissions updated"})


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

@app.route("/patient_names")
def patient_names():
    patients = []
    try:
        with open("patients.csv", newline='', encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                name = row.get("Patient name", "").strip()
                cancer = row.get("Cancer type", "").strip()
                if name:
                    patients.append({"name": name, "cancer": cancer})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
    return jsonify({"success": True, "patients": patients})

@app.route("/get_patient", methods=["GET"])
def get_patient():
    name = request.args.get("name", "").strip().lower()
    try:
        with open("patients.csv", newline='', encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get("Patient name", "").strip().lower() == name:
                    return jsonify({"success": True, "patient": row})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
    return jsonify({"success": False, "error": "Patient not found"}), 404
@app.route("/update_patient", methods=["POST"])
def update_patient():
    data = request.get_json()

    if not data or "Patient name" not in data:
        return jsonify({"success": False, "error": "Missing patient name"}), 400

    updated = False
    patient_id = None

    try:
        # Load existing patients
        with open("patients.csv", newline='', encoding="utf-8") as f:
            patients = list(csv.DictReader(f))

        for row in patients:
            if row["Patient name"].strip().lower() == data["Patient name"].strip().lower():
                row.update({
                    "Patient age": data.get("Patient age", row.get("Patient age", "")),
                    "Diagnosis type": data.get("Diagnosis type", row.get("Diagnosis type", "")),
                    "Cancer type": data.get("Cancer type", row.get("Cancer type", "")),
                    "Country": data.get("Country", row.get("Country", "")),
                    "County": data.get("County", row.get("County", "")),
                })
                updated = True
                break

        if not updated:
            return jsonify({"success": False, "error": "Patient not found"}), 404

        # Save updated CSV
        with open("patients.csv", "w", newline='', encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=patients[0].keys())
            writer.writeheader()
            writer.writerows(patients)

        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/screen_patients", methods=["POST"])
def screen_patients():
    try:
        result = run_screening()
        return jsonify({"success": True, "result": result})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)
