import openai
import os, sys, argparse
import subprocess
import shutil

parser = argparse.ArgumentParser(description="Create a Python script from a prompt string and a test script",
                                 formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument("prompt", help="Prompt for the script, will be appended with a condition the script needs to pass the test passed to 'test'")
parser.add_argument("output_file", help="Path to where the output will be written.  Needs to be in location your test_file.py will find it")
parser.add_argument("--test_file", help="[Optional] Path to the test_file.py you have created that the generated script will need to pass. If excluded will attempt to generate one and pause for you to inspect it")
args = parser.parse_args()
config = vars(args)

# Set up OpenAI API
openai.api_key = os.environ["OPENAI_API_KEY"]

# Function to request code generation from the OpenAI API
def request_code(prompt, temperature=0.5):
    print("Requesting code generation")
    print("================================================")
    print(prompt)
    response = openai.Completion.create(
        model="text-davinci-003",
        prompt=prompt,
        max_tokens=1500,
        n=1,
        stop=None,
        temperature=temperature,
    )
    code = response.choices[0].text.strip()
    # sometimes lots of weird prefix to the python code 
    return code

# Save generated code to a file
def save_to_file(filename, content):
    with open(filename, "w") as file:
        file.write(content)

# Main workflow
def main():
    # Request code to calculate the sum of the first 100 prime numbers
    test_file = config["test_file"]
    output_file = config["output_file"]
    input_prompt = config["prompt"]
    req_path = os.path.dirname(output_file)
    test_file_only = False

    if test_file == None or not os.path.isfile(test_file) :
        test_file_only = True
        print("Attempting to create test file.  Review it and if looks ok run again with this test file to generate code")
        test_file = os.path.join(req_path, "test_" + os.path.basename(output_file))
        output_file = test_file
        code_description = f"""
Write Python test code using unittest that can test a Python script with this objective: {input_prompt}. 
The test will be sitting in the same directory as the python script to be tested, which is called: {output_file}
"""
    else:
        with open(test_file, "r") as f:
            tests = f.read()
        code_description = f"""
Write Python code with this objective: {input_prompt}. 
The code needs to pass this test python code:
{tests}
"""

    if test_file_only:
        code = request_code(code_description, temperature=0.2)
        save_to_file(output_file, code)
        print ("================================")
        print ("==TEST CODE==========================")
        print(code)
        print (f"Inspect test file {output_file} and rerun via:")
        print (f"python code_generation/create_script.py '{config['prompt']}' {config['output_file']} --test_file {config['test_file']}")
        sys.exit()
    
    code = request_code(code_description)
    print ("================================")
    print ("==CODE==========================")
    print(code)
    save_to_file(output_file, code)

    # Run the tests
    test_result = subprocess.run(["python", test_file], capture_output=True, text=True)
    print(test_result.stderr)

    # Handle test failures and request updated code
    tries = 0
    while test_result.returncode != 0 and tries <= 3:
        tries += 1
        error_description = f"""This is the python code you generated: \n{code}\n\n
This is the test code:\n {tests}\n\n
The tests failed with this error:\n{test_result.stderr}\n
Modify and return the code so that the test code will pass. Remove any invalid characters that create syntax errors.
If the test failed due to an error not associated with the code, return the input code but starting with a commented line starting with NOCODEERROR and a description on what is wrong"""
        code = request_code(error_description)
        shutil.copyfile(output_file, 
                        os.path.join(req_path, f"generation_{tries}.txt"))
        
        if "NOCODEERROR" in code:
            print("Error not associated with code?")
        
        print ("New code run: " + code)
        save_to_file(output_file, code)

        # Rerun the tests
        test_result = subprocess.run(["python", test_file], capture_output=True, text=True)
        print(test_result.stdout)
    
    if test_result.returncode == 0:
        print("Succesfully created code that passes tests:\n " + code)
    else:
        print("Unsuccessfully created code:\n " + code)

if __name__ == "__main__":
    main()
