import requests
import csv
import os
import re
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import TimeoutException, NoSuchElementException

BASE_URL = 'https://www.cancertrials.ie/current-trials/breast/'
OUTPUT_DIR = "trials_data"  # Folder to store CSV files

# Ensure output directory exists
os.makedirs(OUTPUT_DIR, exist_ok=True)

def get_all_trial_links():
    """Scrapes and returns all trial links from the main page."""
    current_page = BASE_URL
    links = []

    while current_page:
        print(f"Scraping page: {current_page}")
        page = requests.get(current_page)
        soup = BeautifulSoup(page.text, 'html.parser')

        # Extract "Read More" links from the current page
        for trial in soup.select('.inside-article'):
            read_more = trial.select_one('a.btn-login.btn-xs')
            if read_more:
                links.append(read_more['href'])

        # Find the "Next" page link
        next_button = soup.select_one('a.next.page-numbers')
        current_page = next_button['href'] if next_button else None

    return links

def sanitize_filename(name):
    """Sanitizes filename by removing spaces and special characters."""
    return "".join(c if c.isalnum() or c == "-" else "_" for c in name)

def extract_detailed_info_link(soup, trial_url):
    """Finds the 'For more detailed information' link, compares it with trial_url."""
    info_link = soup.select_one('h2 + a.btn-login')
    if info_link and 'href' in info_link.attrs:
        detailed_url = urljoin(trial_url, info_link['href'])
        return "n/a" if detailed_url == trial_url else detailed_url
    return "n/a"

def extract_participation_criteria_link(detailed_url):
    """Generates the 'Participation Criteria' link by appending '#participation-criteria'."""
    return f"{detailed_url}#participation-criteria" if detailed_url != "n/a" else "n/a"

def extract_eligibility_criteria_selenium(participation_url):
    """Extracts 'Eligibility Criteria' using Selenium, with better error handling."""
    if participation_url == "n/a":
        print("Participation URL not found")
        return "n/a"

    print(f"Fetching Eligibility Criteria from {participation_url} using Selenium...")

    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

    try:
        driver.get(participation_url)

        # Attempt to wait for Eligibility Criteria section
        try:
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.XPATH, "//div[contains(text(), 'Eligibility Criteria')]"))
            )
        except TimeoutException:
            print(f"Timeout: No 'Eligibility Criteria' section found for {participation_url}")
            return "n/a"

        soup = BeautifulSoup(driver.page_source, "html.parser")

        # Try known class names
        criteria_section = None
        possible_classes = [
            "participation-content", "ctg-long-text", "text-container",
            "text-block", "usa-prose", "section-content", "eligibility-criteria-description"
        ]

        for class_name in possible_classes:
            criteria_section = soup.find("div", class_=class_name)
            if criteria_section:
                print(f"Found eligibility section: {class_name}")
                break

        # If no known sections are found, check for the keyword in text
        if not criteria_section:
            criteria_section = soup.find(string=re.compile("Eligibility Criteria", re.IGNORECASE))
            if criteria_section:
                criteria_section = criteria_section.find_parent("div")

        # Final fallback check
        if not criteria_section:
            print(f"No eligibility criteria section found on {participation_url}. Skipping.")
            return "n/a"

        # Extract text
        page_text = criteria_section.get_text(" ", strip=True)

        # Extract Inclusion & Exclusion Criteria
        inclusion_match = re.search(r"Inclusion Criteria[:\s]*(.*?)Exclusion Criteria", page_text, re.DOTALL | re.IGNORECASE)
        exclusion_match = re.search(r"Exclusion Criteria[:\s]*(.*)", page_text, re.DOTALL | re.IGNORECASE)

        inclusion_text = inclusion_match.group(1).strip() if inclusion_match else "n/a"
        exclusion_text = exclusion_match.group(1).strip() if exclusion_match else "n/a"

        return f"Inclusion: {inclusion_text} || Exclusion: {exclusion_text}"

    except Exception as e:
        print(f"Error extracting eligibility criteria from {participation_url}: {e}")
        return "n/a"

    finally:
        driver.quit()


def extract_trial_data(url):
    """Extracts tabular data from a trial page, adds extra details, and saves it as a CSV file."""
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
    eligibility_criteria = extract_eligibility_criteria_selenium(participation_criteria_link)

    all_data.append(["More Detailed Information:", detailed_info_link])
    all_data.append(["Participation Criteria Link:", participation_criteria_link])
    all_data.append(["Eligibility Criteria:", eligibility_criteria])

    filename = os.path.join(OUTPUT_DIR, f"{trial_name}.csv")
    with open(filename, mode="w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerows(all_data)

    print(f"Saved: {filename}")

trial_links = get_all_trial_links()
for link in trial_links:
    extract_trial_data(link)
