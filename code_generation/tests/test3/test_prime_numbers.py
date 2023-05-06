import unittest
import prime_numbers

class TestPrimeNumbers(unittest.TestCase):
    def test_sum_of_first_100_prime_numbers(self):
        result = prime_numbers.sum_of_first_100_prime_numbers()
        self.assertEqual(result, 24133)

if __name__ == '__main__':
    unittest.main()