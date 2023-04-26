import openai
import os, sys, argparse, re
import subprocess
import shutil
from langchain.chat_models import ChatOpenAI
from langchain.chains import ConversationChain
from langchain.memory import ConversationBufferWindowMemory
from langchain.callbacks import get_openai_callback


parser = argparse.ArgumentParser(description="Create a Python script from a prompt string and a test script",
                                 formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument("prompt", help="Prompt for the script, will be appended with a condition the script needs to pass the test passed to 'test'")
parser.add_argument("output_file", help="Path to where the output will be written.  Needs to be in location your test_file.py will find it")
parser.add_argument("--test_file", help="[Optional] Path to the test_file.py you have created that the generated script will need to pass. If excluded will attempt to generate one and pause for you to inspect it")
args = parser.parse_args()
config = vars(args)

# Set up OpenAI API
openai.api_key = os.environ["OPENAI_API_KEY"]

chat = ChatOpenAI(temperature=0.4)

memory = ConversationBufferWindowMemory(k=5)

def parse_code(code):
    text = ""
    if "```" in code:
        match = re.search('(.+?)\`\`\`(python)?\n(.*?)\`\`\`\n(.+?)', code, re.DOTALL)
        if not match:
            print("Couldn't find any code in API response\n", code)
            return None
        code = match.group(3)
        if match and match.group(1) is not None:
            text = match.group(1)
        if match and match.group(4) is not None:
            text = text + match.group(4)
    else:
        memory.chat_memory.add_user_message("You MUST always enclose your code examples with three backticks (```)")
    
    return code, text

# Function to request code generation from the OpenAI API
def request_code(prompt):
    print("================================================")
    print("==    Requesting code generation              ==")
    print("================================================")
    
    memory.chat_memory.add_user_message("You are an expert AI to help create Python programs. You always enclose your code examples with three backticks (```)")

    with get_openai_callback() as cb:
        chain = ConversationChain(
            llm=chat,
            #verbose=True,
            memory=memory)
        code = chain.predict(input=prompt)
        print(cb)

    # sometimes lots of weird prefix to the python code 
    code, text = parse_code(code)
    print("==AI FEEDBACK==")
    print(text)
    
    return code + '\n\n"""\n' + text + '"""\n'

# Save generated code to a file
def save_to_file(filename, content, type="w"):
    with open(filename, type) as file:
        file.write(content)

def create_test_file_and_exit(config):

    test_file = config["test_file"]
    output_file = config["output_file"]
    input_prompt = config["prompt"]
    req_path = os.path.dirname(output_file)

    print("==CREATE TEST FILE ======================================================")
    print("== Attempting to create test file.")  
    print("== Review. If looks ok run again including test file to generate code")
    print("=========================================================================")
    test_file = os.path.join(req_path, "test_" + os.path.basename(output_file))
    output_file = test_file

    # create prompt to pass in to LLM
    prompt = f"""
Write Python test code using unittest that can test a Python script with this objective: {input_prompt}. 
The test will be sitting in the same directory as the python script to be tested called: {output_file}
Only return the Python code. Comment the code well."""

    code = request_code(prompt)

    # save to file and exit for user to inspect
    save_to_file(output_file, code)

    print ("==TEST CODE==========================")
    print(code)
    print("==USER INPUT NEEDED================")
    print (f"==Inspect test file {output_file} and then rerun via:")
    print (f"""
python code_generation/create_script.py '{config['prompt']}' {config['output_file']} --test_file {config['test_file']}
    """)
    sys.exit()

# Main workflow
def main():
    # Request code to calculate the sum of the first 100 prime numbers
    test_file = config["test_file"]
    output_file = config["output_file"]
    input_prompt = config["prompt"]
    req_path = os.path.dirname(output_file)

    if test_file == None or not os.path.isfile(test_file):
        create_test_file_and_exit(config)
    
    with open(test_file, "r") as f:
        tests = f.read()
    prompt = f"""
Write Python code with this objective: {input_prompt}. 
The code needs to pass this test python code:
{tests}
"""
    
    code = request_code(prompt)
    save_to_file(output_file, code)

    # Run the tests
    print ("==CODE TESTS STARTING: INTIAL==========================")
    test_result = subprocess.run(["python", test_file], capture_output=True, text=True)
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
        code = request_code(error_description)

        shutil.copyfile(output_file, 
                        os.path.join(req_path, f"generation_{tries}.txt"))
        
        print (f"===Code retry {tries}")
        save_to_file(output_file, code)

        # Rerun the tests
        print (f"==CODE TESTS RETRY: {tries} ==========================")
        test_result = subprocess.run(["python", test_file], capture_output=True, text=True)
        print(test_result.stdout)

    if test_result.returncode == 0:
        print("===Succesfully created code that passes tests :) =================")
    else:
        print("===Unsuccessful in creatng code ;( ================================")
    print(f"Prompt: {input_prompt}")
    print(f"Test File: {test_file}")
    print(f"Output File: {output_file}")


if __name__ == "__main__":
    main()
