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

