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
import re
from transformers import pipeline

negative_sign_regex = "-?[$€£¥₣₹]?"
number_regex = "(?:\\d+)((\\d{1,3})*([\\,\\ ]\\d{3})*)(\\.\\d+)?"
label_regex = "((k|m|b)(\\s|$|\\.| ))|((thousand)|(million)|(billion)|(trillion)|(thousands)|(millions)|(billions)|(trillions)"
full_label_regex = f"([ ]?({label_regex}))?)"

date_regex = "\\d{1,2}\\/\\d{1,2}\\/\\d{2,4}"
phone_number_regex = "[1-9]\\d{2}-\\d{3}-\\d{4}|\\(\\d{3}\\)\\s?\\d{3}-\\d{4}|[1-9]\\d{2}\\.\\d{3}\\.\\d{4}"

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
    regex_header = re.compile(f'{date_regex}|{phone_number_regex}')
    text = re.sub(regex_header, '', text)
    return text

# Extract numbers and potential labels from text
# See https://regexr.com/84dku for details on the regex + test cases
def extract_potential_numbers(text):
    text = text.lower()
    full_regex = f'{negative_sign_regex}{number_regex}{full_label_regex}'
    regex_header = re.compile(full_regex)
    potential_numbers = re.finditer(regex_header, text)
    final_ans = []
    for pn in potential_numbers:
        number_rep = pn.group(0)
        split_by_decimal = number_rep.split(".")
        # Filter out number if it is split by decimal and there are more than 2 parts, ie 12.3123.14
        if len(split_by_decimal) > 2:
            continue
        is_valid_number = True
        # Filter out numbers split by strange spacing. ie: 3131 31 31 is not a valid number
        split_by_spaces = split_by_decimal[0].split(" ")
        for ind, split in enumerate(split_by_spaces):
            num_digits = len([ch for ch in split if ch.isdigit()])
            if ind != 0 and num_digits != 3:
                is_valid_number = False
            if ind == 0 and num_digits > 3:
                is_valid_number = False
        # Filter out numbers split by strange commas. ie:1 363,021 388,333 423,378 is not a valid number
        split_by_commas = split_by_decimal[0].split(",")
        for ind, split in enumerate(split_by_commas):
            num_digits = len([ch for ch in split if ch.isdigit()])
            if ind != 0 and num_digits != 3:
                is_valid_number = False
            if ind == 0 and num_digits > 3:
               is_valid_number = False
        if is_valid_number:
            final_ans.append(number_rep)
    return final_ans

def clean_number(text):
    cleaned_text = ''.join(map(str, [char for char in text if char.isdigit() or char == "."])).rstrip(".")
    num = float(cleaned_text)
    regex_header = re.compile(f'((k|m|b|t)(\\s|$|\\.| ))|((thousand)|(million)|(billion)|(trillion)|(thousands)|(millions)|(billions)|(trillions))')
    factor = re.search(regex_header, text)
    if factor and factor.group():
        multiplier = language_to_number[factor.group().strip().strip('.')]
        num = num * multiplier
    return num

def get_highest_number(text):
    text = remove_false_positives(text)
    potential_numbers = extract_potential_numbers(text)
    highest_number, highest_number_text = 0, ""
    for pn in potential_numbers:
        number = clean_number(pn)
        if number > highest_number:
            highest_number = number
            highest_number_text = pn
    return highest_number, highest_number_text

def get_largest_number_in_pdf(filename):
    largest_number, largest_match, page = 0, "", -1
    with pdfplumber.open(filename) as pdf:
        for current_page in range(0, len(pdf.pages)):
            page_content = pdf.pages[current_page]
            # Check tables for large numbers
            tables = page_content.extract_tables(table_settings={})
            for table in tables:
                for row in table:
                    for item in row:
                        if item is not None and len(item) > 0:
                            largest_table_number, matched_text = get_highest_number(item)
                            if largest_table_number > largest_number:
                                largest_number, largest_match, page = largest_table_number, matched_text, current_page
            # Check text for large numbers
            text = page_content.extract_text()
            largest_text_number, matched_text = get_highest_number(text)
            if largest_text_number > largest_number:
                largest_number, largest_match, page = largest_text_number, matched_text, current_page
    return largest_number, largest_match, page+1

def main():
    ans, largest_match, page = get_largest_number_in_pdf("AirForce.pdf")
    if page < 0:
        print(f'No numbers found in the PDF file')
        return
    print(f'The largest number in the PDF file is {ans} which was found from the regex match {largest_match} on page {page}')

main()