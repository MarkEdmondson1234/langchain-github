# Adventures in LLMs for Code Generation

## setup

```
python3 -m venv env
source env/bin/activate
./env/bin/python3 -m pip install -r requirements.txt
```

Get an [OpenAPI key](https://platform.openai.com/account/api-keys) then put it in environment variables

```
echo 'export OPENAI_API_KEY=12345' >> ~/.zshenv
source ~/.zshenv
```

## Cloud and local disk based Long term message class

I plan to run all prompts and responses through a class that will save it to disk or publish it to a PubSub topic. 

This opens up many use cases where an organization could have all usage of LLMs sent to one BigQuery database, or for triggers to be based on the content of those messages e.g. if a LLM response includes a template: SQL: {the_sql} then it could run that query; if an LLM response includes a template keyword EMAIL: {email_content} then it could send an email etc. etc. 

Messages are also stored into a vector database, so that they can be searched over to provide context to the LLM, which improves its responses for data that is not within its training set. 

### setup

Login to gcloud and init

```
gcloud config configurations activate default
gcloud auth login
```

You may need this if changed previously:

```
gcloud auth application-default login
```

```
# specify the GCP project you want to publish PubSub messages to, or it will take the gcloud default.
echo 'export GOOGLE_CLOUD_PROJECT=12345' >> ~/.zshenv

# location for where to save .json newline delimited messages
echo 'export MESSAGE_HISTORY=/Users/mark/dev/ml/chat_history/ >> ~/.zshenv
source ~/.zshenv
```

### Sending messages to PubSub

The example script below will save all messages to disk at the `MESSAGE_HISTORY` location; save message history to a Chroma database for QnA retrieval at `MESSAGE_HISTORY/chroma/.` (for adding context to prompts) and send messages to PubSub for use later on (say write to a BigQuery table, or trigger a Cloud Function to parse templates, etc. etc.)


#### LLM generated description

This code sets up an OpenAI chat model and uses it to generate responses to prompts. It imports several modules, including os, my_llm, and langchain. The code sets up an OpenAI API key and initializes a ChatOpenAI object with a temperature of 0.4. It also initializes a memory object with the namespace "debugger" and clears it. The code then generates a response to the prompt "How many ways are there to travel between the north pole and Copenhagen directly?" using the request_llm function from my_llm. It prints the response and generates a second response to a prompt that asks for a Danish translation of the first response. Finally, the code applies a summarization function to the memory object and prints the resulting summary. The memory object is then saved to a vector store.

#### Code

```python

import os
import my_llm.standards as my_llm
import openai
from langchain.chat_models import ChatOpenAI
from my_llm.langchain_class import PubSubChatMessageHistory

# swap out for any other LLM supported by LangChain
openai.api_key = os.environ["OPENAI_API_KEY"]
chat = ChatOpenAI(temperature=0.4)

# has methods memory.add_user_message() and memory.add_ai_message() that are used to write to disk and pubsub
memory = PubSubChatMessageHistory("debugger")

# clears any messages from local disk
memory.clear()

# the animal is random to demonstrate it is used in the context search later
prompt = "How many ways are there to travel between the north pole and Copenhagen directly? Also output a random animal with prefix: ANIMAL:"

# Uses a langchain ConversationChain as per /my_llm/standards.py
answer = my_llm.request_llm(prompt, chat, memory)

print(answer)

prompt2 = f"""
Repeat the answer below but in Danish, or if you don't know just say 'munch munch' a lot:
{answer}
"""

answer2 = my_llm.request_llm(prompt2, chat, memory)


# creates a summary message of the messages stored so far
summary = memory.apply_summarise_to_memory()

print("Summary")
print(summary)

# this vectorstore is stored only locally (for now)
memory.save_vectorstore_memory()

# it searches over the vectorstore, and inserts context into the prompt before sending the answer to LLM
answer3 = memory.question_memory("What random animal have you said?")
print(answer3)
```

### Load Chat-GPT history from its export file

In Chat-GPT you can export your chat history as a json file.  There is a parser to load this into a vectorstore and publish to PubSub.

The below example imports the history of when I was creating these scripts - we can see it answers about context that was only obtained through chat history for this library, after the training cutoff date.

```python
import os
import my_llm.standards as my_llm
import openai
from langchain.chat_models import ChatOpenAI
from my_llm.langchain_class import PubSubChatMessageHistory

# Set up OpenAI API
openai.api_key = os.environ["OPENAI_API_KEY"]

chat = ChatOpenAI(temperature=0.4)

memory = PubSubChatMessageHistory("debugger")
memory.clear()
# load chat-gpt history
memory.load_chatgpt_export("chatgpt_export/conversations.json")

summary = memory.apply_summarise_to_memory(n=10)

print("Summary last 10 messages")
print(summary)

memory.save_vectorstore_memory()

answer3 = memory.question_memory("How is a TimedChatMessage defined?")
print(answer3)
```

#### output:

```
Project ID: devo-mark-sandbox
Cleared memory
Loaded chatgpt_export/conversations.json into messages
Summary last 10 messages

The human asks the AI to adjust a task so messages are published to Google PubSub when they are written to disk. The AI is asked to make pubsub_topic an optional variable when the class is created. The human also inquires about the purpose of the "memory_namespace: str" line in the class and whether it is necessary to be there. The AI is asked to adjust the task so that if pubsub_topic is not passed, it will create the pubsub_topic from memory_namespace.

Saving Chroma DB at /Users/mark/dev/ml/chat_history/debugger/chroma/ ...
Using embedded DuckDB with persistence: data will be stored in: /Users/mark/dev/ml/chat_history/debugger/chroma/

Loading Chroma DB from /Users/mark/dev/ml/chat_history/debugger/chroma/.
Using embedded DuckDB with persistence: data will be stored in: /Users/mark/dev/ml/chat_history/debugger/chroma/
 
 A TimedChatMessage is an object that contains a message and a role (e.g. "user") that is used in the BaseChatMessageHistory class and its subclasses.
 ````

## QnA over a directory

This utility imports files from a directory into a Chroma vector store, which is then used to provide context to the LLM for when you ask questions about that directory.

Configure location for vector store and make it executable:

```
echo 'export CHROMA_DB_PATH=/Users/mark/dev/ml/chat_history/' >> ~/.zshenv
source ~/.zshenv
chmod u+x qna/read_repo.py
```

Help here:

```

> ./qna/read_repo.py -h
usage: read_repo.py [-h] [--reindex] [--ext EXT] [--ignore IGNORE] [--resummarise] repo

Chat with a GitHub repository

positional arguments:
  repo             The GitHub repository on local disk

optional arguments:
  -h, --help       show this help message and exit
  --reindex        Whether to re-index the doc database that supply context to the Q&A (default: False)
  --ext EXT        Comma separated list of file extensions to include. Defaults to '.md,.py' (default: None)
  --ignore IGNORE  Directory to ignore file imports from. Defaults to 'env/' (default: None)
  --resummarise    Recreate the code.md files describing the code (default: False)
```

On first run it will create the database.  To make the QnA more useful, it will also generate .md files for any scripts you have indicated you want to read (e.g. script.py will have script.md generated in the same folder).  You can see examples in this repository.

You can renew the database by using the --reindex option, and recreate the summaries with the --resummarise option.

```
# Read this directory ($PWD)
python qna/read_repo.py $PWD
```

It lets you ask questions in the command line:

```
Loading Chroma DB from ./chroma/langchain-github.
Using embedded DuckDB with persistence: data will be stored in: ./chroma/langchain-github

Ask a question. CTRL + C to quit.
```

You can specify what file extensions you want to include in the database, and which folders to ignore.  The default ignores the `env/` folder, typically as its used for `venv`

```
# make a new database to include all .md/.py/.txt files
python qna/read_repo.py $PWD --reindex --ext='.md,.py,.txt'
Creating Chroma DB at ./chroma/langchain-github ...
Ignoring /Users/mark/dev/ml/langchain/read_github/langchain-github/env
Reading .md files
Read 1 and ignored 9 .md files.
Reading .py files
Read 16 and ignored 11130 .py files.
Reading .txt files
Read 9 and ignored 170 .txt files.
Read all files
Using embedded DuckDB with persistence: data will be stored in: ./chroma/langchain-github

Ask a question. CTRL + C to quit.
What is this repo about?

Answer:
I don't know.
== Document sources:
 - README.md
 - qna/read_repo.py
 - README.md
 - qna/read_repo.py


Ask a question. CTRL + C to quit.
summarise this readme

Answer: This utility imports files from a directory into a Chroma vector store, which is then used to provide context to the LLM for when you ask questions about that directory. You can specify what file extensions you want to include and what directories to ignore when importing documents.
== Document sources:
 - argparse_example.py
 - README.md
 - qna/read_repo.py
 - qna/read_repo.py
```

## Code generation

Make it executable:

```
chmod u+x code_generation/create_script.py
```

See help:

```
python code_generation/create_script.py --help
usage: create_script.py [-h] prompt test_file output_file

Create a Python script from a prompt string and a test script

positional arguments:
  prompt       Prompt for the script, will be appended with a condition the script needs to pass the test passed to 'test'
  test_file    Path to the test_file.py you have created that the generated script will need to pass
  output_file  Path to where the output will be written. Needs to be in location your test_file.py will find it

optional arguments:
  -h, --help   show this help message and exit
```

### Create your script

Some examples of how it was used to make scripts.

#### Sum of first 100 primes

1. Make a test file your generated script must pass:

```python
# saved to test1/test_prime_numbers.py
import unittest

from prime_numbers import prime_sum

class TestPrimeNumberFunctions(unittest.TestCase):
    def test_sum_of_first_100_prime_numbers(self):
        self.assertEqual(prime_sum(), 24133)

if __name__ == '__main__':
    unittest.main()
```

2. Make a prompt for your script: "Compute the sum of the first 100 prime numbers"
3. Use `code_generation/create_script.py` to generate the python script and test it:

```
ls test1
#test_prime_numbers.py
python code_generation/create_script.py \
 "Compute the sum of the first 100 prime numbers" \
 test1/prime_numbers.py \
 --test_file test1/test_prime_numbers.py
 

ls test1
#generation_1.txt        prime_numbers.py        test_prime_numbers.py
```

Result:

````
Requesting code generation
================================================

Write Python code with this objective: Compute the sum of the first 100 prime numbers. 
The code needs to pass this test python code:
import unittest

from prime_numbers import prime_sum

class TestPrimeNumberFunctions(unittest.TestCase):
    def test_sum_of_first_100_prime_numbers(self):
        self.assertEqual(prime_sum(), 24133)

if __name__ == '__main__':
    unittest.main()

================================
==CODE==========================
def prime_sum():
    prime_numbers = [2]
    num = 3
    while len(prime_numbers) < 100:
        for p in prime_numbers:
            if num % p == 0:
                break
        else:
            prime_numbers.append(num)
        num += 2
    return sum(prime_numbers)
.
----------------------------------------------------------------------
Ran 1 test in 0.000s

OK

Succesfully created code that passes tests: def prime_sum():
    prime_numbers = [2]
    num = 3
    while len(prime_numbers) < 100:
        for p in prime_numbers:
            if num % p == 0:
                break
        else:
            prime_numbers.append(num)
        num += 2
    return sum(prime_numbers)
````

#### Generic prime number counting

1. Make a test_file for your functionality

```python
# saved to test2/test_prime_numbers.py
import unittest

from prime_numbers import prime_sum

class TestPrimeNumberFunctions(unittest.TestCase):
    def test_sum_of_first_100_prime_numbers(self):
        self.assertEqual(prime_sum(100), 24133)
    def test_sum_of_first_10_prime_numbers(self):
        self.assertEqual(prime_sum(10), 129)

if __name__ == '__main__':
    unittest.main()
```

2. Make a prompt for your script: "Compute the sum of the first N prime numbers"
3. Use `code_generation/create_script.py` to generate the python script and test it:

```
ls test2
#test_prime_numbers.py
python code_generation/create_script.py \
  "Compute the sum of the first N prime numbers" \
  test2/prime_numbers.py \
  --test_file test2/test_prime_numbers.py

ls test2
# prime_numbers.py        test_prime_numbers.py
```

Result:

```python
Requesting code generation
================================================

Write Python code with this objective: Compute the sum of the first N prime numbers. 
The code needs to pass this test python code:
import unittest

from prime_numbers import prime_sum

class TestPrimeNumberFunctions(unittest.TestCase):
    def test_sum_of_first_100_prime_numbers(self):
        self.assertEqual(prime_sum(100), 24133)
    def test_sum_of_first_10_prime_numbers(self):
        self.assertEqual(prime_sum(10), 129)

if __name__ == '__main__':
    unittest.main()

================================
==CODE==========================
def prime_sum(N): 
    prime_numbers = [2]
    x = 3
    while len(prime_numbers) < N:
        for y in range(3,x,2):  # test all odd factors up to x-1
            if x%y == 0:
                x += 2
                break
        else:
            prime_numbers.append(x)
            x += 2
    return sum(prime_numbers)
..
----------------------------------------------------------------------
Ran 2 tests in 0.001s

OK

Succesfully created code that passes tests: def prime_sum(N): 
    prime_numbers = [2]
    x = 3
    while len(prime_numbers) < N:
        for y in range(3,x,2):  # test all odd factors up to x-1
            if x%y == 0:
                x += 2
                break
        else:
            prime_numbers.append(x)
            x += 2
    return sum(prime_numbers)
```

#### Generate the test_function too

1. Make a prompt you want a python function to do: "Compute how many hours there have been since now and given dates in YYYY-mm-dd:HH:MM format"
2. Generate a test_file for your functionality

```
python code_generation/create_script.py \
  "Compute how many hours there have been since now and given dates in YYYY-mm-dd:HH:MM format" \
  test4/how_many_hours.py --test_file=test4/test_how_many_hours.py
```

It will exit for you to inspect the test file, since it needs this to be accurate to generate code successfully.

3. Run the command again to generate python code that passes the tests.  It will iterate over the results if the test errors attempting to make a better file that will pass the tests.

```
python code_generation/create_script.py \
  "Compute how many hours there have been since now and given dates in YYYY-mm-dd:HH:MM format" \
  test4/how_many_hours.py --test_file=test4/test_how_many_hours.py
````

#### Black hole evaporation

1. Make a prompt

````
export LLM_PROMPT="Compute how long in years a black hole will evaporate via Hawking Radition.  Show examples for a black hole the same mass the Earth"
````

2. Generate a test_file for your functionality

```
mkdir test5
python code_generation/create_script.py $LLM_PROMPT \
  test5/black_holes.py --test_file=test5/test_black_holes.py
```

It often hallicinates the actual values for the earth mass etc. so it needs to have them corrected using this website as the source of truth: https://www.vttoth.com/CMS/physics-notes/311-hawking-radiation-calculator

It states that the Earth weighs 1.98900E30 kgs and a black hole the same mass would evaporate in 1.15975E67 years.  Other than that its usually a pretty good test file, for example:

```
import unittest
from black_holes import compute_evaporation_time

class TestBlackHoles(unittest.TestCase):

    def test_earth_mass(self):
        # Test a black hole with the same mass as the Earth
        # (I changed below to the correct numbers)
        mass = 1.98900e+30  # kg 
        expected_time = 1.15975e+67  # years 
        self.assertAlmostEqual(compute_evaporation_time(mass), expected_time)

if __name__ == '__main__':
    unittest.main()
```

This can improve in the future by verifying using Agent Tools

3. Create code via

```python
python code_generation/create_script.py $LLM_PROMPT \
  test5/black_holes.py --test_file=test5/test_black_holes.py
```

It never got it correct in the few times I tried it iterating 4 times, but the numbers are very variable.  The code was at least helpful for a human to finish off.

#### Generating yaml files for Cloud Build

I need this quite a lot at work.

1. Make a prompt.  I had to iterate over this a few times to get the test file I wanted.

````
export LLM_PROMPT="Create one python file that contains one helper function for making yaml files that are valid for Google Cloud Platform's Cloud Build service.  The test will use the python yaml generator to test the validity of the yaml, for an example task of building a Dockerfile for a python script."
````

2. Generate a test_file for your functionality

```
mkdir test6
python code_generation/create_script.py $LLM_PROMPT \
  test6/gcp_cloud_build.py --test_file=test6/test_gcp_cloud_build.py
```

3. Generate the code based off the test_file.

```
python code_generation/create_script.py $LLM_PROMPT \
  test6/gcp_cloud_build.py --test_file=test6/test_gcp_cloud_build.py
```

This iterated a few times but then was successful:

````
================================================
==    Requesting code generation              ==
================================================
Tokens Used: 898
        Prompt Tokens: 404
        Completion Tokens: 494
Successful Requests: 1
Total Cost (USD): $0.0017959999999999999
==AI FEEDBACK==
Great! Here's an example helper function that creates a valid yaml file for Google Cloud Platform's Cloud Build service:



==CODE TESTS STARTING: INTIAL==========================
F
======================================================================
FAIL: test_valid_yaml (__main__.TestGcpCloudBuild)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/Users/mark/dev/ml/langchain/read_github/langchain-github/test6/test_gcp_cloud_build.py", line 33, in test_valid_yaml
    self.assertEqual(generated_yaml, expected_yaml)
AssertionError: {'images': ['gcr.io/gcr.io/my-project/my-im[96 chars]r'}]} != {'steps': [{'name': 'gcr.io/cloud-builders/[89 chars]ge']}
- {'images': ['gcr.io/gcr.io/my-project/my-image'],
?              -------

+ {'images': ['gcr.io/my-project/my-image'],
   'steps': [{'args': ['build', '-t', 'my-image', '.'],
              'name': 'gcr.io/cloud-builders/docker'}]}

----------------------------------------------------------------------
Ran 1 test in 0.002s

FAILED (failures=1)

================================================
==    Requesting code generation              ==
================================================
Tokens Used: 1401
        Prompt Tokens: 1173
        Completion Tokens: 228
Successful Requests: 1
Total Cost (USD): $0.002802
==AI FEEDBACK==
I apologize for the error in the previous code. Here's the updated code that should pass the test:



===Code retry 1
==CODE TESTS RETRY: 1 ==========================

================================================
==    Requesting code generation              ==
================================================
Tokens Used: 1936
        Prompt Tokens: 1711
        Completion Tokens: 225
Successful Requests: 1
Total Cost (USD): $0.003872
==AI FEEDBACK==
I apologize for the mistake again. Here's the updated code that should pass the test:



===Code retry 2
==CODE TESTS RETRY: 2 ==========================

================================================
==    Requesting code generation              ==
================================================
Tokens Used: 2129
        Prompt Tokens: 1904
        Completion Tokens: 225
Successful Requests: 1
Total Cost (USD): $0.004258
==AI FEEDBACK==
I apologize for the mistake again. Here's the updated code that should pass the test:



===Code retry 3
==CODE TESTS RETRY: 3 ==========================

================================================
==    Requesting code generation              ==
================================================
Tokens Used: 1889
        Prompt Tokens: 1670
        Completion Tokens: 219
Successful Requests: 1
Total Cost (USD): $0.003778
==AI FEEDBACK==
I apologize for the mistake again. Here's the updated code that should pass the test:



===Code retry 4
==CODE TESTS RETRY: 4 ==========================

===Succesfully created code that passes tests :) =================
Prompt: Create one python file that contains one helper function for making yaml files that are valid for Google Cloud Platform's Cloud Build service.  The test will use the python yaml generator to test the validity of the yaml, for an example task of
building a Dockerfile for a python script.
Test File: test6/test_gcp_cloud_build.py
Output File: test6/gcp_cloud_build.py
````

## Architecture

Map-reduce for each function with its own test.
Agent to create the tasks that the function will do.  Break up the tasks.  Give it a tool.

