# Adventures in LLMs for Code Generation

## setup

```
python3 -m venv env
source env/bin/activate
python3 -m pip install -r requirements.txt
```

Get an [OpenAPI key](https://platform.openai.com/account/api-keys) then put it in environment variables

```
echo 'export OPENAI_API_KEY=12345' >> ~/.zshenv
source ~/.zshenv
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
 test1/test_prime_numbers.py \
 test1/prime_numbers.py

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
  test2/test_prime_numbers.py \
  test2/prime_numbers.py

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
````
