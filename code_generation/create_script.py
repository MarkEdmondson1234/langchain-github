import openai
import os, sys
import subprocess
import shutil

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
    test_file = "code_generation/test_prime_numbers.py"
    with open(test_file, "r") as f:
        tests = f.read()

    file_location = "code_generation/prime_numbers.py"

    code_description = f"Write Python code to calculate the sum of the first 100 prime numbers. The code needs to pass this test python code saved in file test_prime_numbers.py:\n{tests}"
    code = request_code(code_description)
    print ("================================")
    print ("==CODE==========================")
    print(code)
    save_to_file(file_location, code)

    # Request test code for the prime number functions
    #test_description = "Write Python unittest tests for the prime number functions in the given code snippet."
    #tests = request_code(test_description + "\n\n" + code)
    #print ("================================")
    #print ("==TEST CODE=====================")
    #print(tests)
    #save_to_file("test_prime_numbers.py", tests)

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
        shutil.copyfile(file_location, f"code_generation/prime_numbers_{tries}.txt")
        
        if "NOCODEERROR" in code:
            print(code)
            sys.exit()
        
        print ("New code run: " + code)
        save_to_file(file_location, code)

        # Rerun the tests
        test_result = subprocess.run(["python", test_file], capture_output=True, text=True)
        print(test_result.stdout)
    
    if test_result.returncode == 0:
        print("Succesfully created code that passes tests: " + code)
    else:
        print("Unsuccessfully created code: " + code)

if __name__ == "__main__":
    main()
