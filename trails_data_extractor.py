import re
import json

# Function to read the document from a file
def read_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        return file.read()

# Function to parse the document
def parse_document(document):
    # Regex patterns
    key_value_pattern = re.compile(r'^([^,:]+):,(.*)$')  # Updated regex to capture multi-line values
    section_pattern = re.compile(r'-{50,}')  # Matches section separators (----)

    # Initialize data structure
    data = {}
    current_section = None

    # Parse the document
    for line in document.split('\n'):
        if section_pattern.match(line):
            current_section = None  # Reset section
        elif key_value_pattern.match(line):
            match = key_value_pattern.match(line)
            key = match.group(1).strip()
            value = match.group(2).strip()
            if current_section:
                data[current_section][key] = value
            else:
                data[key] = value
        elif line.strip():  # Handle multi-line fields
            if current_section:
                data[current_section][key] += ' ' + line.strip()
            else:
                data[key] += ' ' + line.strip()

    return data

# Function to split eligibility criteria into individual values
def split_criteria(section):
    # Split by periods (.) and filter out empty strings
    criteria = [c.strip() for c in re.split(r'\.\s*', section) if c.strip()]
    return criteria

# Main function to process the file
def process_file(file_path):
    # Read the document from the file
    document = read_file(file_path)

    # Parse the document
    data = parse_document(document)

    # Extract eligibility criteria
    eligibility_criteria = data.get("Eligibility Criteria", "")

    # Split into inclusion and exclusion sections
    if "||" in eligibility_criteria:
        inclusion_section, exclusion_section = eligibility_criteria.split("||")
    else:
        inclusion_section, exclusion_section = eligibility_criteria, ""

    # Clean up the sections
    inclusion_section = inclusion_section.replace("Inclusion:", "").strip()
    exclusion_section = exclusion_section.replace("Exclusion:", "").strip()

    # Get individual inclusion and exclusion criteria
    inclusion_criteria = split_criteria(inclusion_section)
    exclusion_criteria = split_criteria(exclusion_section)

    # Add separated criteria to the data structure
    data["Inclusion Criteria"] = inclusion_criteria
    data["Exclusion Criteria"] = exclusion_criteria

    # Return structured data
    return data

# File path to the document
file_path = r"C:\Users\erykd\Downloads\TREAT_ctDNA_study.csv"  # Replace with your file path

# Process the file and get structured data
structured_data = process_file(file_path)

# Print structured data
print(json.dumps(structured_data, indent=4))

# Optionally, save the structured data to a JSON file
with open("output.json", "w", encoding="utf-8") as json_file:
    json.dump(structured_data, json_file, indent=4)
