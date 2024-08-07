"""
We chose a solution using pdfplumber because it can extract tables and appears to have more advanced functionality than PyPDF2

Our solution involves fairly complex regex, we've linked each regex to a regexr.com page where you can see test cases and details

Future improvements (short term)
- Mark numbers like ($31321.32) or $(40) as negative, especially inside table cells
- In tables, take into account labels such as "Dollars in Millions" in the first cell of a row, or at the top of a column
- Consider extracting numbers from images inside the PDF file
- Remove more false positives such as IP addresses, times, more date formats, and legal code headings
- Reconsider whether to throw an exception if no numbers are found, or return 0

Future improvements (long term)
- Use an LLM with instruction fine tuning on a larger model with training sets of PDFs to extract numbers that can only be identified via bidirectional context
    - Evaluate precision / recall of models with training data (may need human labeling)
"""


import pdfplumber
import sys
import re

potential_negative_sign = "-?[$€£¥₣₹]?"
potential_number_regex = "(?:\d+)((\d{1,3})*([\,\ ]\d{3})*)(\.\d+)?"
potential_label_regex = "[ ]?(k[^a-zA-Z]|m[^a-zA-Z]|b[^a-zA-Z]|t[^a-zA-Z]|thousand|million|billion|trillion|thousands|millions|billions|trillions)?"

date_regex = "\d{1,2}\/\d{1,2}\/\d{2,4}"
phone_number_regex = "[1-9]\d{2}-\d{3}-\d{4}|\(\d{3}\)\s?\d{3}-\d{4}|[1-9]\d{2}\.\d{3}\.\d{4}"

language_to_number = {
    "k": 1000,
    "m": 1000000,
    "b": 1000000000,
    "t": 1000000000000,
    "thousand": 1000,
    "million": 1000000,
    "billion": 1000000000,
    "trillion": 1000000000000,
    "thousands": 1000,
    "millions": 1000000,
    "billions": 1000000000,
    "trillions": 1000000000000,
}

# Remove clear false positives such as dates and phone numbers
# See https://regexr.com/84dlj for details on the regex + test cases
# Note: this won't remove all dates or phone numbers, only the most obvious ones. We don't want too many false negatives
def remove_false_positives(text):
    print(f'Removing false positives from text {text}') # TODO(JSHU): Remove this print statement
    regex_header = re.compile(f'{date_regex}|{phone_number_regex}')
    text = re.sub(regex_header, '', text)
    print(f'After removing false positives from text {text}') # TODO(JSHU): Remove this print statement
    return text

# Extract numbers and potential labels from text
# See https://regexr.com/84dku for details on the regex + test cases
def extract_potential_numbers(text):
    text = text.lower()
    full_regex = f'{potential_negative_sign}{potential_number_regex}{potential_label_regex}'
    print(f'Extracting numbers with regex: {full_regex} from text {text}') # TODO(JSHU): Remove this print statement
    regex_header = re.compile(full_regex)
    potential_numbers = re.findall(regex_header, text)
    print(f'Found potential numbers: {potential_numbers}') # TODO(JSHU): Remove this print statement
    return potential_numbers

def clean_number(text):
    num = float(str([char for char in text if char.isdigit() or char == "."]))
    factor = re.find(potential_label_regex, text)
    if factor:
        factor = language_to_number[factor]
        num = num * factor
    return 0, text

def get_highest_number(text):
    text = remove_false_positives(text)
    potential_numbers = extract_potential_numbers(text)
    highest_number, highest_number_text = -1 * sys.maxsize, ""
    for pn in potential_numbers:
        print(f'Cleaning potential number: {pn}') # TODO(JSHU): Remove this print statement
        number = clean_number(pn)
        if number > highest_number:
            highest_number = number
            highest_number_text = pn
    return highest_number, highest_number_text

def get_largest_number_in_pdf(filename):
    largest_number, largest_match, page = sys.maxsize * -1, "", 0
    with pdfplumber.open(filename) as pdf:
        for current_page in range(0, len(pdf.pages)):
            page_content = pdf.pages[current_page]
            # Check tables for large numbers
            tables = page_content.extract_tables(table_settings={})
            for table in tables:
                for row in table:
                    for item in row:
                        if item is not None and len(item) > 0:
                            print("Checking table item", item) # TODO(JSHU): Remove this print statement
                            largest_table_number, matched_text = get_highest_number(item)
                            if largest_table_number > largest_number:
                                largest_number = largest_table_number
                                largest_match = matched_text
            # Check text for large numbers
            text = page_content.extract_text()
            largest_text_number, matched_text = get_highest_number(text)
            if largest_text_number > largest_number:
                print(f'Found new largest number {largest_text_number} from {matched_text} on page {current_page}')
                largest_number = largest_text_number
                largest_match = matched_text
                page = current_page
            # TODO(JSHU): Make sure data in tables is not repeated in text
    if largest_number == -1 * sys.maxsize:
        raise ValueError("No valid numbers found in the PDF")
    return largest_number, largest_match, page

def main():
    try:
        ans, largest_match, page = get_largest_number_in_pdf("AirForce.pdf")
    except ValueError as e:
        print(f'Could not find largest number: {e}')
        return
    print(f'The largest number in the PDF file is {ans} which was found from the regex match {largest_match} on page {page}')

main()