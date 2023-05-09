#!/Users/mark/dev/ml/langchain/read_github/langchain_github/env/bin/python
# change above to the location of your local Python venv installation
import sys, os

parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(parent_dir)

import openai
import os
import subprocess
import shutil
from langchain.chat_models import ChatOpenAI
from my_llm import standards as my_llm

# Set up OpenAI API
openai.api_key = os.environ["OPENAI_API_KEY"]

chat = ChatOpenAI(temperature=0.4)

memory = my_llm.init_memory("create_script")

def create_test_file_and_exit(config, test_file):

    output_file = config["output_file"]
    input_prompt = config["prompt"]

    print("==CREATE TEST FILE ======================================================")
    print("== Attempting to create test file.")  
    print("== Review. If looks ok run again including test file to generate code")
    print("=========================================================================")
    output_file = test_file

    # create prompt to pass in to LLM
    prompt = f"""
Write Python test code using unittest that will unit test an existing Python script in the same directory that has been written with this objective: 
{input_prompt}. 
Do not call any external APIs or services, use mocking functions instead. The test should be able to be run in a self contained manner.
The test will be sitting in the same directory as the python script to be tested called: {output_file}
"""

    code = my_llm.request_code(prompt, chat, memory)

    # save to file and exit for user to inspect
    my_llm.save_to_file(output_file, code)

    print ("==TEST CODE==========================")
    print(code)
    print("==USER INPUT NEEDED================")
    print (f"==Inspect test file {output_file} and then rerun via:")
    print (f"""
python code_generation/create_script.py '{config['prompt']}' {config['output_file']} --test_file {config['test_file']}
    """)
    sys.exit()

def run_python_test(test_file):
    python_executable = sys.executable  # Get the full path to the Python executable
    result = subprocess.run([python_executable, test_file], capture_output=True, text=True)

    return result


# Main workflow
def main(config):
    # Request code to calculate the sum of the first 100 prime numbers
    test_file = config["test_file"]
    output_file = config["output_file"]
    input_prompt = config["prompt"]
    req_path = os.path.dirname(output_file)

    if test_file == None:
        # see if test file exists
        test_file = os.path.join(req_path, "test_" + os.path.basename(output_file))
        print(f"Using test file: {test_file}")

    if not os.path.isfile(test_file):
        create_test_file_and_exit(config, test_file)
    
    with open(test_file, "r") as f:
        tests = f.read()
    prompt = f"""
Write Python code with this objective: {input_prompt}. 
The code needs to pass this test python code:
{tests}
"""
    
    code = my_llm.request_code(prompt, chat, memory)
    my_llm.save_to_file(output_file, code)

    # Run the tests
    print ("==CODE TESTS STARTING: INTIAL==========================")
    test_result = run_python_test(test_file)
    print(test_result.stderr)

    # Handle test failures and request updated code
    tries = 0
    while test_result.returncode != 0 and tries <= 3:
        tries += 1
        test_errors = test_result.stderr
        error_description = f"""The code you created in the last response has failed the test.
Modify and return the code so that the test code will pass. Remove any invalid characters that create syntax errors.
The tests failed with this error:\n{test_errors}\n
"""
        code = my_llm.request_code(error_description, chat, memory)

        shutil.copyfile(output_file, 
                        os.path.join(req_path, f"generation_{tries}.txt"))
        
        print (f"===Code retry {tries}")
        my_llm.save_to_file(output_file, code)

        # Rerun the tests
        print (f"==CODE TESTS RETRY: {tries} ==========================")
        test_result = run_python_test(test_file)

    if test_result.returncode == 0:
        print("===Succesfully created code that passes tests :) =================")
    else:
        print("===Unsuccessful in creatng code ;( ================================")
    print(f"Prompt: {input_prompt}")
    print(f"Test File: {test_file}")
    print(f"Output File: {output_file}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Create a Python script from a prompt string and a test script",
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("prompt", help="Prompt for the script, will be appended with a condition the script needs to pass the test passed to 'test'")
    parser.add_argument("output_file", help="Path to where the output will be written.  Needs to be in location your test_file.py will find it")
    parser.add_argument("--test_file", help="[Optional] Path to the test_file.py you have created that the generated script will need to pass. If excluded will attempt to generate one and pause for you to inspect it")
    args = parser.parse_args()
    config = vars(args)

    main(config)
