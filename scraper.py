
import requests
import csv
import os
import re
import time
from bs4 import BeautifulSoup
from urllib.parse import urljoin

CANCER_URLS = {
    "Breast": "https://www.cancertrials.ie/current-trials/breast/",
    "Lung": "https://www.cancertrials.ie/current-trials/lung/",
    "Multiple Myeloma": "https://www.cancertrials.ie/current-trials/lymphoma-blood-cancers/multiple-myeloma/",
    "Genitourinary": "https://www.cancertrials.ie/current-trials/genitourinary/",
    "CLL": "https://www.cancertrials.ie/current-trials/lymphoma-blood-cancers/chronic-lymphocytic-leukaemia-cll/"
}

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

def extract_trial_data(url, country, cancer_type):
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')

    tables = soup.select('table.table')
    if not tables:
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
    eligibility_criteria = extract_eligibility_from_api(extract_nct_id_from_url(participation_criteria_link))

    all_data.append(["More Detailed Information:", detailed_info_link])
    all_data.append(["Participation Criteria Link:", participation_criteria_link])
    all_data.append(["Eligibility Criteria:", eligibility_criteria])

    cancer_dir = os.path.join("trials_data", country.lower().replace(" ", "_"), cancer_type.lower().replace(" ", "_"))
    os.makedirs(cancer_dir, exist_ok=True)
    filename = os.path.join(cancer_dir, f"{trial_name}.csv")

    with open(filename, mode="w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerows(all_data)

    return filename

def get_all_trial_links(base_url):
    current_page = base_url
    links = []

    while current_page:
        page = requests.get(current_page)
        soup = BeautifulSoup(page.text, 'html.parser')
        for trial in soup.select('.inside-article'):
            read_more = trial.select_one('a.btn-login.btn-xs')
            if read_more:
                links.append(read_more['href'])

        next_button = soup.select_one('a.next.page-numbers')
        current_page = next_button['href'] if next_button else None

    return links
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

        print(f"Saved EU trial: {filename}")

def scrape_trials(cancer_type, country="Ireland"):
    if country == "Ireland":
        base_url = CANCER_URLS.get(cancer_type)
        trial_links = get_all_trial_links(base_url)
        saved_files = []
        for link in trial_links:
            try:
                saved_files.append(extract_trial_data(link, country, cancer_type))
            except Exception as e:
                print(f"Error with trial: {link} -> {e}")
        return saved_files
    else:
        output_dir = os.path.join("trials_data", country.lower().replace(" ", "_"))
        extract_trial_data_in_eu(cancer_type, country, output_dir)
        return [f"Trials for {cancer_type} in {country} saved."]