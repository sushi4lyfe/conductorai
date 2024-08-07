import pdfplumber
import re
import transformers

model_name = "distilbert-base-cased-distilled-squad"
llm = transformers.pipeline("question-answering", model_name)

language_to_number = {
    "thousand": 1000,
    "million": 1000000,
    "billion": 1000000000,
    "trillion": 1000000000000,
    "thousands": 1000,
    "millions": 1000000,
    "billions": 1000000000,
    "trillions": 1000000000000,
}

# The most effective prompt is the second prompt. The third prompt has more examples, but it is less effective likely
# due to multiple $X millions examples which may lead the model to believe million is a better match than higher cardinality numbers
# We will need more diverse examples and more complex fine tuning to improve the model's performance.
# Simply adding "billion" a bunch of times in the prompt will cause overfitting, and not work for other generalized cases.

LARGEST_NUMBER_PROMPTS = [
    # Basic prompt
    "What is the largest number in this document?",
    # Few shot prompt
    "Find the biggest value. For example, $321 billion, or 293, or $23 million.",
    # Few shot prompt with even more examples
    "Find the biggest value. For example, $321 billion, 84 million, 100K, 293, or $23.53 million.",
]

# is_valid_number: check if the text extracted by the ML model is a valid number
# considered using LLM categorization task for this, but faster to do via regex
def is_valid_number(text):
    text = text.strip().lower()
    # Filter out clearly non-numerical output with alphabetical characters in between two sets of numbers
    invalid_number_regex = '[0-9]+[\\S\\s]*[a-zA-Z$]+[\\S\\s]*[0-9]+'
    regex_search_term = re.compile(f'{invalid_number_regex}')
    if re.search(regex_search_term, text):
        return False
    cleaned_text = ''.join(map(str, [char for char in text if char.isdigit() or char == "." or char == ","])).rstrip(".")
    # Filter out numbers that are empty or have more than one decimal point
    if cleaned_text == "" or cleaned_text.count(".") > 1:
        return False
    split_by_decimal = cleaned_text.split(".")
    split_by_commas = split_by_decimal[0].split(",")
    # Filter out numbers with commas in the wrong place
    for ind, split in enumerate(split_by_commas):
        num_digits = len([ch for ch in split if ch.isdigit()])
        if (ind != 0 and num_digits != 3) or (ind == 0 and num_digits > 3 and len(split_by_commas) > 1):
            return False
    return True

# clean_number: convert the extracted text to a number
# considered using an LLM translation task for this but couldn't find a good existing model
def clean_number(text):
    cleaned_text = ''.join(map(str, [char for char in text.strip().lower() if char.isdigit() or char == "."])).rstrip(".")
    num = float(cleaned_text)
    regex_header = re.compile(f'(thousand)|(million)|(billion)|(trillion)|(thousands)|(millions)|(billions)|(trillions)')
    factor = re.search(regex_header, text)
    if factor and factor.group():
        multiplier = language_to_number[factor.group().strip().strip('.')]
        num = num * multiplier
    return num

# get_largest_number_with_ml: given a filename, extract the largest number from the PDF file
# uses question / answer LLM to extract the largest number from each page and return the largest number found
def get_largest_number_with_ml(filename, prompt):
    largest_number, largest_match, page = 0, "", -1
    with pdfplumber.open(filename) as pdf:
        for current_page in range(0, len(pdf.pages)):
            page_content = pdf.pages[current_page]
            text = page_content.extract_text()
            answer = llm(question=prompt, context=text)['answer']
            if is_valid_number(answer) and clean_number(answer) > largest_number:
                largest_number, largest_match, page = clean_number(answer), answer, current_page
    return largest_number, largest_match, page+1

def main():
    for prompt in LARGEST_NUMBER_PROMPTS:
        ans, largest_match, page = get_largest_number_with_ml("AirForce.pdf", prompt)
        if page < 0:
            print(f'No numbers found in the PDF file')
            return
        print(f'The largest number is {ans} which was extracted from {largest_match} on page {page} using prompt \'{prompt}\'')

main()