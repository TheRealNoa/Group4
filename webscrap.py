import tkinter as tk
import requests
import csv
import os
import re
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import threading
import time

# Cancer type URLs
CANCER_URLS = {
    "Breast": "https://www.cancertrials.ie/current-trials/breast/",
    "Lung": "https://www.cancertrials.ie/current-trials/lung/",
    "Multiple Myeloma": "https://www.cancertrials.ie/current-trials/lymphoma-blood-cancers/multiple-myeloma/",
    "Genitourinary": "https://www.cancertrials.ie/current-trials/genitourinary/",
    "CLL": "https://www.cancertrials.ie/current-trials/lymphoma-blood-cancers/chronic-lymphocytic-leukaemia-cll/"
}
EU_COUNTRIES = [
    "Ireland", "Austria", "Belgium", "Bulgaria", "Croatia", "Cyprus", "Czech Republic",
    "Denmark", "Estonia", "Finland", "France", "Germany", "Greece", "Hungary", "Italy",
    "Latvia", "Lithuania", "Luxembourg", "Malta", "Netherlands", "Poland", "Portugal",
    "Romania", "Slovakia", "Slovenia", "Spain", "Sweden"
]

API_QUERY_MAP = {
    "Breast": "Breast Cancer",
    "Lung": "Lung Cancer",
    "Multiple Myeloma": "Multiple Myeloma",
    "Genitourinary": "Prostate Cancer",
    "CLL": "Chronic Lymphocytic Leukemia"
}
def sanitize_filename(name):
    return "".join(c if c.isalnum() or c == "-" else "_" for c in name)

def extract_detailed_info_link(soup, trial_url):
    info_link = soup.select_one('h2 + a.btn-login')
    if info_link and 'href' in info_link.attrs:
        detailed_url = urljoin(trial_url, info_link['href'])
        return "n/a" if detailed_url == trial_url else detailed_url
    return "n/a"

def extract_participation_criteria_link(detailed_url):
    return f"{detailed_url}#participation-criteria" if detailed_url != "n/a" else "n/a"

def extract_eligibility_from_api(nct_id):
    import requests
    api_url = f"https://clinicaltrials.gov/api/v2/studies/{nct_id}"
    try:
        response = requests.get(api_url, timeout=10)
        response.raise_for_status()
        data = response.json()
        eligibility = data.get("protocolSection", {}).get("eligibilityModule", {}).get("eligibilityCriteria", "")
        return eligibility if eligibility else "n/a"
    except Exception as e:
        return f"API error: {e}"

def extract_nct_id_from_url(url):
    match = re.search(r"(NCT\d+)", url)
    return match.group(1) if match else None

def extract_eligibility_criteria(participation_url):
    if participation_url == "n/a":
        print(" No participation URL provided.")
        return "n/a"

    nct_id = extract_nct_id_from_url(participation_url)
    if not nct_id:
        print(f" Could not extract NCT ID from: {participation_url}")
        return "n/a"

    print(f"📡 Fetching eligibility via API for {nct_id}...")
    eligibility_text = extract_eligibility_from_api(nct_id)
    
    if eligibility_text != "n/a":
        print(" Retrieved eligibility text via API.")
        return f"Eligibility Criteria: {eligibility_text}"
    else:
        print(f" No eligibility criteria found via API for {nct_id}")
        return "n/a"

def extract_trial_data(url, country, cancer_type):
    print(f"Extracting trial data from {url}")
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')

    tables = soup.select('table.table')
    if not tables:
        print(f"No tables found on {url}")
        return

    trial_name = "Unknown_Trial"
    all_data = []

    for table in tables:
        rows = table.find_all("tr")
        for row in rows:
            cols = row.find_all(["td", "th"])
            cols = [col.get_text(" ", strip=True) for col in cols]
            if cols and "Name:" in cols[0]:
                trial_name = sanitize_filename(cols[1])
            all_data.append(cols)
        all_data.append(["-" * 50])

    detailed_info_link = extract_detailed_info_link(soup, url)
    participation_criteria_link = extract_participation_criteria_link(detailed_info_link)
    eligibility_criteria = extract_eligibility_criteria(participation_criteria_link).strip("Eligibility Criteria")

    all_data.append(["More Detailed Information:", detailed_info_link])
    all_data.append(["Participation Criteria Link:", participation_criteria_link])
    all_data.append([f"Eligibility Criteria: {eligibility_criteria}"])

    # Save in: trials_data/ireland/<cancer_type>/<trial_name>.csv
    cancer_dir = os.path.join("trials_data", country.lower().replace(" ", "_"), cancer_type.lower().replace(" ", "_"))
    os.makedirs(cancer_dir, exist_ok=True)
    filename = os.path.join(cancer_dir, f"{trial_name}.csv")

    with open(filename, mode="w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerows(all_data)

    print(f"✅ Saved: {filename}")

def get_all_trial_links(base_url):
    current_page = base_url
    links = []

    while current_page:
        print(f"Scraping page: {current_page}")
        page = requests.get(current_page)
        soup = BeautifulSoup(page.text, 'html.parser')

        for trial in soup.select('.inside-article'):
            read_more = trial.select_one('a.btn-login.btn-xs')
            if read_more:
                links.append(read_more['href'])

        next_button = soup.select_one('a.next.page-numbers')
        current_page = next_button['href'] if next_button else None

    return links


def threaded_scrape_with_timestamp(cancer_type, status_label, update_times, country="Ireland"):
    status_label.config(text=f"{cancer_type}: Updating...")
    update_times[cancer_type] = time.time()

    try:
        if country == "Ireland":
            base_url = CANCER_URLS[cancer_type]
            trial_links = get_all_trial_links(base_url)
            for link in trial_links:
                extract_trial_data(link, country, cancer_type)
        else:
            output_dir = os.path.join("trials_data", country.lower().replace(" ", "_"))
            extract_trial_data_in_eu(cancer_type, country, output_dir)

        update_times[cancer_type] = time.time()
        status_label.config(text=f"{cancer_type}: Last updated just now.")
    except Exception as e:
        status_label.config(text=f"{cancer_type}: Error: {e}")


def fetch_eu_trials(cancer_type, country):
    url = "https://clinicaltrials.gov/api/v2/studies"
    headers = {"Accept": "application/json"}
    params = {
        "query.cond": API_QUERY_MAP.get(cancer_type, cancer_type),
        "query.locn": country,
        "filter.overallStatus": "RECRUITING|NOT_YET_RECRUITING",
        "pageSize": 50
    }

    try:
        response = requests.get(url, params=params, headers=headers)
        response.raise_for_status()
        data = response.json()
        return data.get("studies", [])
    except Exception as e:
        print(f"API error for {cancer_type} in {country}: {e}")
        return []



def extract_trial_data_in_eu(cancer_type, country, output_dir):
    trials = fetch_eu_trials(cancer_type, country)
    if not trials:
        print(f"No trials found for {cancer_type} in {country}")
        return

    # Create subdirectory: country/cancer_type/
    cancer_dir = os.path.join(output_dir, cancer_type.lower().replace(" ", "_"))
    os.makedirs(cancer_dir, exist_ok=True)

    for idx, trial in enumerate(trials, start=1):
        ps = trial.get("protocolSection", {})
        id_mod = ps.get("identificationModule", {})
        status_mod = ps.get("statusModule", {})
        sponsor_mod = ps.get("sponsorCollaboratorsModule", {})
        design_mod = ps.get("designModule", {})
        eligibility_mod = ps.get("eligibilityModule", {})

        # Extract data fields
        nct_id = id_mod.get("nctId", f"trial{idx}")
        title = id_mod.get("briefTitle", "n/a")
        full_title = id_mod.get("officialTitle", "n/a")
        sponsor = sponsor_mod.get("leadSponsor", {}).get("name", "n/a")
        pi = sponsor_mod.get("leadSponsor", {}).get("agencyClass", "n/a")
        start_date = status_mod.get("startDateStruct", {}).get("date", "n/a")
        eligibility = eligibility_mod.get("eligibilityCriteria", "n/a")

        # Format file content
        rows = []
        rows.append(["Name:", title])
        rows.append(["Number:", str(idx)])
        rows.append(["Full Title:", full_title])
        rows.append(["-" * 50])
        if pi != "n/a":
            rows.append(["Principal Investigator:", pi])
        rows.append(["Type:", design_mod.get("studyType", "n/a")])
        rows.append(["Sponsor:", sponsor])
        rows.append(["Recruitment Started:", f"Global: {start_date}"])
        rows.append(["-" * 50])
        base_url = f"https://clinicaltrials.gov/study/{nct_id}"
        rows.append(["More Detailed Information:", base_url])
        rows.append(["Participation Criteria Link:", f"{base_url}#participation-criteria"])
        rows.append(["Eligibility Criteria:", f"Eligibility Criteria: {eligibility}"])

        # Save trial
        filename = os.path.join(cancer_dir, f"{sanitize_filename(nct_id)}.csv")
        with open(filename, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerows(rows)

        print(f"✅ Saved EU trial: {filename}")


# --- GUI Code ---
def run_gui():
    root = tk.Tk()
    root.title("Cancer Trials Scraper")
    root.geometry("500x600")

    # --- COUNTRY & COUNTY SELECTION ---
    location_frame = tk.Frame(root)
    location_frame.pack(pady=10)

    tk.Label(location_frame, text="Select Country:", font=("Helvetica", 12)).grid(row=0, column=0, sticky="w")
    selected_country = tk.StringVar(value="Ireland")
    country_dropdown = tk.OptionMenu(location_frame, selected_country, *EU_COUNTRIES)
    country_dropdown.grid(row=1, column=0, padx=5)

    tk.Label(location_frame, text="County (if Ireland):", font=("Helvetica", 10)).grid(row=0, column=1, sticky="w")
    counties = [
        "Antrim", "Armagh", "Carlow", "Cavan", "Clare", "Cork", "Derry", "Donegal",
        "Down", "Dublin", "Fermanagh", "Galway", "Kerry", "Kildare", "Kilkenny",
        "Laois", "Leitrim", "Limerick", "Longford", "Louth", "Mayo", "Meath",
        "Monaghan", "Offaly", "Roscommon", "Sligo", "Tipperary", "Tyrone",
        "Waterford", "Westmeath", "Wexford", "Wicklow"
    ]
    selected_county = tk.StringVar(value="Dublin")
    county_dropdown = tk.OptionMenu(location_frame, selected_county, *counties)
    county_dropdown.grid(row=1, column=1, padx=5)

    def update_county_visibility(*args):
        if selected_country.get() == "Ireland":
            county_dropdown.grid()
        else:
            county_dropdown.grid_remove()

    selected_country.trace_add("write", update_county_visibility)
    update_county_visibility()

    # --- CANCER TYPE SELECTION ---
    tk.Label(root, text="Select Cancer Type:", font=("Helvetica", 12)).pack()
    selected_cancer_type = tk.StringVar(value=list(CANCER_URLS.keys())[0])
    cancer_dropdown = tk.OptionMenu(root, selected_cancer_type, *CANCER_URLS.keys())
    cancer_dropdown.pack(pady=5)

    # --- PATIENT INFO ---
    tk.Label(root, text="Patient Information", font=("Helvetica", 12)).pack(pady=10)

    patient_name_var = tk.StringVar()
    tk.Label(root, text="Patient Name:").pack()
    tk.Entry(root, textvariable=patient_name_var).pack()

    patient_age_var = tk.StringVar()
    tk.Label(root, text="Patient Age:").pack()
    tk.Entry(root, textvariable=patient_age_var).pack()

    tk.Label(root, text="Diagnosis Type:").pack()
    diagnosis_type_var = tk.StringVar(value="Newly Diagnosed")
    diagnosis_dropdown = tk.OptionMenu(root, diagnosis_type_var, "Newly Diagnosed", "Relapsed")
    diagnosis_dropdown.pack()

    # --- SCRAPE BUTTON ---
    status_labels = {}
    update_times = {}

    def start_scraping():
        country = selected_country.get()
        cancer_type = selected_cancer_type.get()
        name = patient_name_var.get()
        age = patient_age_var.get()
        diagnosis = diagnosis_type_var.get()

        if not name or not age:
            tk.messagebox.showerror("Missing Info", "Please fill in all patient fields.")
            return

        print(f"🧍 Patient: {name}, Age: {age}, Diagnosis: {diagnosis}")
        print(f"🌍 Country: {country}, Cancer Type: {cancer_type}")
        if country == "Ireland":
            print(f"📍 County: {selected_county.get()}")

        frame = tk.Frame(root)
        frame.pack(pady=3)
        label = tk.Label(frame, text=f"{cancer_type}: Starting...", width=45, anchor="w", fg="blue")
        label.pack(side="left")
        status_labels[cancer_type] = label

        threading.Thread(
            target=threaded_scrape_with_timestamp,
            args=(cancer_type, label, update_times, country),
            daemon=True
        ).start()

    tk.Button(root, text="Start Scraping", bg="lightblue", command=start_scraping).pack(pady=20)

    root.mainloop()

# Run GUI
if __name__ == "__main__":
    run_gui()
