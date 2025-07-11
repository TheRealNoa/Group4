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
import datetime
import dateutil.parser
app = Flask(__name__)

app.secret_key = 'your-secret-key'

ADMIN_SECRETS_FILE = "admin_secrets.json"

UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

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

def get_user_patient_file():
    return session.get("patient_file")

LOG_FILE = "logs.json"

def add_log(action, user_email, details=""):
    log_entry = {
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
        "email": user_email,
        "action": action,
        "details": details
    }
    logs = {}
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, encoding="utf-8") as f:
            logs = json.load(f)
    if user_email not in logs:
        logs[user_email] = []
    logs[user_email].append(log_entry)
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        json.dump(logs, f, indent=2)

def format_timestamp(ts):
    try:
        dt = dateutil.parser.isoparse(ts)
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except:
        return ts
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


    patient_file = get_user_patient_file()
    patients = []
    if patient_file and os.path.exists(patient_file):
        with open(patient_file, newline='', encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                patients.append({
                    "name": row.get("Patient name", "").strip(),
                    "cancer": row.get("Cancer type", "").strip(),
                    "id": row.get("Patient ID", "").strip()
                })

    return render_template(
        "index.html",
        patient_info=patient_info,
        is_admin=is_admin,
        admin_verified=is_verified,
        patient_list=patients
)

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
    patient_file = get_user_patient_file()
    if not patient_file or not os.path.exists(patient_file):
        return "No patient file uploaded.", 400
    patients = []
    try:
        with open(patient_file, newline='', encoding="utf-8") as f:
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
    patient_file = get_user_patient_file()
    if not patient_file or not os.path.exists(patient_file):
        return "No patient file uploaded.", 400

    patient_id = request.args.get("patient_id", "").strip().lower()
    try:
        with open(patient_file, newline='', encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get("Patient ID", "").strip().lower() == patient_id:
                    return jsonify({"success": True, "patient": row})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
    return jsonify({"success": False, "error": "Patient not found"}), 404

@app.route("/update_patient", methods=["POST"])
def update_patient():
    patient_file = get_user_patient_file()
    if not patient_file or not os.path.exists(patient_file):
        return "No patient file uploaded.", 400

    data = request.get_json()
    if not data or "Patient ID" not in data:
        return jsonify({"success": False, "error": "Missing patient ID"}), 400

    updated = False
    changes = []

    try:
        with open(patient_file, newline='', encoding="utf-8") as f:
            patients = list(csv.DictReader(f))

        for row in patients:
            if row["Patient ID"].strip().lower() == data["Patient ID"].strip().lower():
                for key in row.keys():
                    if key in data:
                        old_value = row[key].strip()
                        new_value = data[key].strip()
                        if old_value != new_value:
                            row[key] = new_value
                            changes.append(f"{key}: '{old_value}' → '{new_value}'")
                if changes:
                    change_details = "; ".join(changes)
                    add_log("EDIT", session["email"], f"Patient ID {data['Patient ID']}: {change_details}")
                updated = True
                break

        if not updated:
            return jsonify({"success": False, "error": "Patient not found"}), 404

        with open(patient_file, "w", newline='', encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=patients[0].keys())
            writer.writeheader()
            writer.writerows(patients)

        if changes:
            change_details = "; ".join([f"{c['field']}: '{c['from']}' -> '{c['to']}'" for c in changes])
            add_log("EDIT", session["email"], f"Patient ID {data['Patient ID']} changes: {change_details}")

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
    
@app.route("/upload_patients", methods=["GET", "POST"])
def upload_patients():
    if not session.get("logged_in"):
        return redirect(url_for("login"))

    if request.method == "POST":
        if "file" not in request.files:
            return "No file part", 400
        file = request.files["file"]
        if file.filename == "":
            return "No selected file", 400
        if file:
            email = session["email"].split("@")[0]
            filename = f"{email}_patients.csv"
            file_path = os.path.join(UPLOAD_FOLDER, filename)
            file.save(file_path)
            session["patient_file"] = file_path
            add_log("UPLOAD", session["email"], f"Uploaded file {filename}")
            return redirect(url_for("home"))

    return render_template("upload_patients.html")

@app.route("/download_patients")
def download_patients():
    if not session.get("logged_in"):
        return redirect(url_for("login"))

    patient_file = get_user_patient_file()
    if not patient_file or not os.path.exists(patient_file):
        return "No patient file uploaded.", 400

    filename = os.path.basename(patient_file)
    add_log("DOWNLOAD", session["email"], f"Downloaded file {filename}")
    return send_file(patient_file, as_attachment=True, download_name=filename)

@app.route("/admin_logs")
def admin_logs():
    if session.get("email") not in ADMIN_EMAILS:
        return jsonify({"error": "Unauthorized"}), 403

    formatted_logs = []
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, encoding="utf-8") as f:
            all_logs = json.load(f)
        for user_logs in all_logs.values():
            for log in user_logs:
                formatted_logs.append({
                    "action": log.get("action", ""),
                    "timestamp": format_timestamp(log.get("timestamp", ""))
                })
    return jsonify({"logs": formatted_logs})

@app.route("/get_user_logs")
def get_user_logs():
    if session.get("email") not in ADMIN_EMAILS:
        return jsonify({"error": "Unauthorized"}), 403

    target_email = request.args.get("email", "").strip().lower()
    if not target_email:
        return jsonify({"error": "Missing email"}), 400

    logs = {}
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, encoding="utf-8") as f:
            logs = json.load(f)

    user_logs = logs.get(target_email, [])
    formatted_logs = [
        {
            "action": log.get("action", ""),
            "timestamp": format_timestamp(log.get("timestamp", "")),
            "details": log.get("details", "")
            
        }
        for log in user_logs
    ]
    return jsonify({"logs": formatted_logs})

@app.route("/delete_user_log", methods=["POST"])
def delete_user_log():
    if session.get("email") not in ADMIN_EMAILS:
        return jsonify({"success": False, "error": "Unauthorized"}), 403

    data = request.get_json()
    target_email = data.get("email")
    timestamp = data.get("timestamp")

    if not target_email or not timestamp:
        return jsonify({"success": False, "error": "Missing data"}), 400

    logs = {}
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, encoding="utf-8") as f:
            logs = json.load(f)

    user_logs = logs.get(target_email, [])
    original_count = len(user_logs)
    user_logs = [log for log in user_logs if log.get("timestamp") != timestamp]
    logs[target_email] = user_logs

    with open(LOG_FILE, "w", encoding="utf-8") as f:
        json.dump(logs, f, indent=2)

    return jsonify({"success": True, "deleted": original_count - len(user_logs)})

@app.route("/delete_all_user_logs", methods=["POST"])
def delete_all_user_logs():
    if session.get("email") not in ADMIN_EMAILS:
        return jsonify({"success": False, "error": "Unauthorized"}), 403

    data = request.get_json()
    target_email = data.get("email")
    if not target_email:
        return jsonify({"success": False, "error": "Missing email"}), 400

    logs = {}
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, encoding="utf-8") as f:
            logs = json.load(f)

    deleted_count = len(logs.get(target_email, []))
    if target_email in logs:
        del logs[target_email]

    with open(LOG_FILE, "w", encoding="utf-8") as f:
        json.dump(logs, f, indent=2)

    return jsonify({"success": True, "deleted": deleted_count})

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)


