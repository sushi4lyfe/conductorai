Original went with a regex based solution, then decided to use LLM. \
\
Just started learning about LLM / huggingdace this week so my model is not super optimized.
I did consider fine tuning and even wrote some code to do it but didn't have time to create a large enough custom dataset in the time allocated.
I think the best solution is the `llmsolution.py` but included both with my submission.
The llmsolution is more elegant, but was initally worse than the regex solution until I added few shot prompting.
One of the prompts performs the same as regex solution but it might be overfitted towards this specific document.
\
\
Overall, thought this project was a ton of fun. Hope to hear back from you guys soon!

## Run the Files

`pip install -r requirements.txt` \
`python llmsolution.py` \
`python regexsolution.py`


## Fine Tuning

Here is some fine tuning code I wrote which I ultimately didn't use, but I've included that as well:

```python
training_set = [
    {
        'answers': {
            'answer_start': [70],
            'text': ['1 million'],
        },
        'context': 'Hey I want 40 burgers or maybe 90. I also want 1000 fries. I also want 1 million',
        'question': 'What is the biggest number in this text?',
    },
    {
        'answers': {
            'answer_start': [19],
            'text': ['2025'],
        },
        'context': 'AFWCF Overview - FY 2025 President’s Budget (PB)',
        'question': 'What is the biggest number in this text?',
    },
    {
        'answers': {
            'answer_start': [50],
            'text': ['239'],
        },
        'context': 'The methodology for calculating cash requirements 239 consists of four from Cash Management',
        'question': 'What is the biggest number in this text?',
    },
]

def tokenize_function(training_data):
    tokenizer = transformers.AutoTokenizer.from_pretrained(model_name)
    return tokenizer(training_data["question"], training_data["context"], truncation=True)

def fine_tune_model():
    model = transformers.AutoModel.from_pretrained(model_name)
    tokenized_train_datasets = map(tokenize_function, training_set)
    training_args = transformers.TrainingArguments(
        output_dir="./smaller_bert_finetuned",
        per_device_train_batch_size=8,
        num_train_epochs=5,
        max_steps=5,
    )
    # Set up trainer, assigning previously set up training arguments
    trainer = transformers.Trainer(
        model=model,
        args=training_args,
        train_dataset=tokenized_train_datasets,
    )
    trainer.train()
```
If we did get it working on a larger dataset, we could probably get it working on for our use case with a high accuracy
rate from just several hundred datapoints. However, since we have a highly specified usecase the model would be prone to
catastrophic forgetting unless we used PEFT or trained alongside broader question types.