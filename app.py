
from flask import Flask, request, jsonify, render_template
import threading
from scraper import scrape_trials

app = Flask(__name__)

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/scrape", methods=["POST"])
def scrape():
    data = request.json
    cancer_type = data.get("cancer_type")
    country = data.get("country", "Ireland")

    print(f"🛰️ Request to scrape {cancer_type} trials in {country}")

    def run_scrape():
        scrape_trials(cancer_type, country)

    threading.Thread(target=run_scrape, daemon=True).start()

    return jsonify({"status": f"Scraping {cancer_type} trials in {country} started."})

if __name__ == "__main__":
    app.run(debug=True)
