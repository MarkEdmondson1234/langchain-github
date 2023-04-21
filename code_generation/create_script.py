import openai
import os, sys, argparse
import subprocess
import shutil

parser = argparse.ArgumentParser(description="Create a Python script from a prompt string and a test script",
                                 formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument("prompt", help="Prompt for the script, will be appended with a condition the script needs to pass the test passed to 'test'")
parser.add_argument("test_file", help="Path to the test_file.py you have created that the generated script will need to pass")
parser.add_argument("output_file", help="Path to where the output will be written.  Needs to be in location your test_file.py will find it")

args = parser.parse_args()
config = vars(args)


# Set up OpenAI API
openai.api_key = os.environ["OPENAI_API_KEY"]

# Function to request code generation from the OpenAI API
def request_code(prompt):
    print("Requesting code generation")
    print("================================================")
    print(prompt)
    response = openai.Completion.create(
        model="text-davinci-003",
        prompt=prompt,
        max_tokens=1500,
        n=1,
        stop=None,
        temperature=0.5,
    )
    return response.choices[0].text.strip()

# Save generated code to a file
def save_to_file(filename, content):
    with open(filename, "w") as file:
        file.write(content)

# Main workflow
def main():
    # Request code to calculate the sum of the first 100 prime numbers
    test_file = config["test_file"]
    with open(test_file, "r") as f:
        tests = f.read()

    output_file = config["output_file"]
    input_prompt = config["prompt"]
    req_path = os.path.dirname(output_file)

    code_description = f"""
Write Python code with this objective: {input_prompt}. 
The code needs to pass this test python code:
{tests}
"""
# If and only if a requirements.txt file is needed for libraries other than 'unittest', provide the libraries in commented out lines at the end of the script after a line '##REQUIREMENTS##',

    code = request_code(code_description)
    print ("================================")
    print ("==CODE==========================")
    print(code)
    save_to_file(output_file, code)
    if '##REQUIREMENTS##' in code:
        req_path = os.path.dirname(output_file)
        req_file = os.path.join(req_path, "requirements.txt")

        reqs = code.split('##REQUIREMENTS##')[1]
        save_to_file(req_file, reqs)
        print(f"==You need to install {req_file} first via 'python3 -m pip install -r requirements.txt'==")
        sys.exit()

    # Run the tests
    test_result = subprocess.run(["python", test_file], capture_output=True, text=True)
    print(test_result.stderr)

    # Handle test failures and request updated code
    tries = 0
    while test_result.returncode != 0 and tries <= 3:
        tries += 1
        error_description = f"""This is the python code you generated: \n{code}\n
This is the test code:\n {tests}\n  
The tests failed with this error:\n{test_result.stderr}\n
Modify and return the code so that the test code will pass.
If the test failed due to an error not associated with the code, return what should be done to fix it with NOCODEERROR as the first word"""
        code = request_code(error_description)
        shutil.copyfile(output_file, 
                        os.path.join(req_path, f"generation_{tries}.txt"))
        
        if "NOCODEERROR" in code:
            print(code)
            sys.exit()
        
        print ("New code run: " + code)
        save_to_file(output_file, code)

        # Rerun the tests
        test_result = subprocess.run(["python", test_file], capture_output=True, text=True)
        print(test_result.stdout)
    
    if test_result.returncode == 0:
        print("Succesfully created code that passes tests: " + code)
    else:
        print("Unsuccessfully created code: " + code)

if __name__ == "__main__":
    main()
