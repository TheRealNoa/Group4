# scraper.py

import requests
import csv
import os
import re
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
    if not nct_id:
        return "Error"  # Explicitly handle 

    api_url = f"https://clinicaltrials.gov/api/v2/studies/{nct_id}"
    try:
        response = requests.get(api_url, timeout=10)
        response.raise_for_status()
        data = response.json()
        eligibility = data.get("protocolSection", {}).get("eligibilityModule", {}).get("eligibilityCriteria")
        return eligibility if eligibility else "n/a"
    except Exception:
        return "Error"

def extract_nct_id_from_url(url):
    match = re.search(r"(NCT\d+)", url)
    return match.group(1) if match else None

def extract_trial_data(url, country, cancer_type):
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    tables = soup.select('table.table')
    if not tables:
        return None

    trial_name = "Unknown_Trial"
    all_data = []

    for table in tables:
        for row in table.find_all("tr"):
            cols = [col.get_text(" ", strip=True) for col in row.find_all(["td", "th"])]
            if cols and "Name:" in cols[0]:
                trial_name = sanitize_filename(cols[1])
            all_data.append(cols)
        all_data.append(["-" * 50])

    detailed_info_link = extract_detailed_info_link(soup, url)
    participation_criteria_link = extract_participation_criteria_link(detailed_info_link)
    eligibility_criteria = extract_eligibility_from_api(extract_nct_id_from_url(participation_criteria_link))

    all_data.extend([
        ["More Detailed Information:", detailed_info_link],
        ["Participation Criteria Link:", participation_criteria_link],
        ["Eligibility Criteria:", eligibility_criteria]
    ])

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
        soup = BeautifulSoup(requests.get(current_page).text, 'html.parser')
        links += [a['href'] for a in soup.select('.inside-article a.btn-login.btn-xs')]
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
        return response.json().get("studies", [])
    except Exception as e:
        print(f"API error for {cancer_type} in {country}: {e}")
        return []

def count_exclusions(eligibility_text):
    if not eligibility_text or eligibility_text.lower().strip() in {"n/a", "na", "error"}:
        return float("inf") 

    eligibility_text = eligibility_text.replace("\r\n", "\n").replace("\r", "\n")

    # Spliting by known exclusion patterns
    sections = re.split(r"(?i)(?:Key )?Exclusion(?: Criteria)?[:\n]", eligibility_text)

    # If no exclusion section found → treat as inclusion-only → sort highest priority
    if len(sections) < 2:
        return -1 

    exclusion_text = sections[1]

    # Count bullets: asterisks or numeric
    bullet_matches = re.findall(r"(?m)^\s*(\*|\d+[.)-]|-)\s+", exclusion_text)

    return len(bullet_matches) if bullet_matches else float("inf")

def extract_trial_data_in_eu(cancer_type, country, output_dir):
    trials = fetch_eu_trials(cancer_type, country)
    if not trials:
        print(f"No trials found for {cancer_type} in {country}")
        return []

    cancer_dir = os.path.join(output_dir, cancer_type.lower().replace(" ", "_"))
    os.makedirs(cancer_dir, exist_ok=True)

    trial_entries = []
    for idx, trial in enumerate(trials, 1):
        ps = trial.get("protocolSection", {})
        id_mod = ps.get("identificationModule", {})
        status_mod = ps.get("statusModule", {})
        sponsor_mod = ps.get("sponsorCollaboratorsModule", {})
        design_mod = ps.get("designModule", {})
        eligibility = ps.get("eligibilityModule", {}).get("eligibilityCriteria", "n/a")

        nct_id = id_mod.get("nctId", f"trial{idx}")
        title = id_mod.get("briefTitle", "n/a")
        exclusion_count = count_exclusions(eligibility)

        rows = [
            ["Name:", title],
            ["Number:", str(idx)],
            ["Full Title:", id_mod.get("officialTitle", "n/a")],
            ["-" * 50],
            ["Type:", design_mod.get("studyType", "n/a")],
            ["Sponsor:", sponsor_mod.get("leadSponsor", {}).get("name", "n/a")],
            ["Recruitment Started:", f"Global: {status_mod.get('startDateStruct', {}).get('date', 'n/a')}"],
            ["-" * 50],
            ["More Detailed Information:", f"https://clinicaltrials.gov/study/{nct_id}"],
            ["Participation Criteria Link:", f"https://clinicaltrials.gov/study/{nct_id}#participation-criteria"],
            ["Eligibility Criteria:", f"Eligibility Criteria: {eligibility}"]
        ]

        filename = os.path.join(cancer_dir, f"{sanitize_filename(nct_id)}.csv")
        trial_entries.append({
            "rows": rows,
            "filename": filename,
            "exclusion_count": exclusion_count
        })

    trial_entries.sort(key=lambda t: t["exclusion_count"])
    for i, entry in enumerate(trial_entries, 1):
        with open(entry["filename"], mode="w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerows(entry["rows"])
        print(f"{i}. {os.path.basename(entry['filename'])} — Exclusions: {entry['exclusion_count']}")

    return [entry["filename"] for entry in trial_entries]

def scrape_trials(cancer_type, country="Ireland"):
    if country == "Ireland":
        # Normalize input to match keys in CANCER_URLS
        cancer_type = cancer_type.strip().title()

        base_url = CANCER_URLS.get(cancer_type)
        if not base_url:
            print(f"No URL found for cancer type: '{cancer_type}'.")
            return []

        trial_links = get_all_trial_links(base_url)
        trial_entries = []

        for link in trial_links:
            try:
                response = requests.get(link)
                soup = BeautifulSoup(response.text, 'html.parser')

                tables = soup.select('table.table')
                if not tables:
                    continue

                trial_name = "Unknown_Trial"
                all_data = []

                for table in tables:
                    for row in table.find_all("tr"):
                        cols = [col.get_text(" ", strip=True) for col in row.find_all(["td", "th"])]
                        if cols and "Name:" in cols[0]:
                            trial_name = sanitize_filename(cols[1])
                        all_data.append(cols)
                    all_data.append(["-" * 50])

                detailed_info_link = extract_detailed_info_link(soup, link)
                participation_criteria_link = extract_participation_criteria_link(detailed_info_link)
                nct_id = extract_nct_id_from_url(participation_criteria_link)
                eligibility = extract_eligibility_from_api(nct_id)

                exclusion_count = count_exclusions(eligibility)

                all_data.extend([
                    ["More Detailed Information:", detailed_info_link],
                    ["Participation Criteria Link:", participation_criteria_link],
                    ["Eligibility Criteria:", eligibility]
                ])

                cancer_dir = os.path.join("trials_data", country.lower().replace(" ", "_"), cancer_type.lower().replace(" ", "_"))
                os.makedirs(cancer_dir, exist_ok=True)
                filename = os.path.join(cancer_dir, f"{trial_name}.csv")

                trial_entries.append({
                    "filename": filename,
                    "rows": all_data,
                    "exclusion_count": exclusion_count
                })

            except Exception as e:
                print(f"Error with trial: {link} -> {e}")

        # Sort Irish trials by exclusion count
        trial_entries.sort(key=lambda t: t["exclusion_count"])
        for i, entry in enumerate(trial_entries, 1):
            with open(entry["filename"], mode="w", newline="", encoding="utf-8") as file:
                csv.writer(file).writerows(entry["rows"])
            print(f"{i}. {os.path.basename(entry['filename'])} — Exclusions: {entry['exclusion_count']}")

        return [entry["filename"] for entry in trial_entries]

    else:
        output_dir = os.path.join("trials_data", country.lower().replace(" ", "_"))
        return extract_trial_data_in_eu(cancer_type, country, output_dir)