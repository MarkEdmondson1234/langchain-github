import unittest

from prime_numbers import prime_sum

class TestPrimeNumberFunctions(unittest.TestCase):
    def test_sum_of_first_100_prime_numbers(self):
        self.assertEqual(prime_sum(100), 24133)
    def test_sum_of_first_10_prime_numbers(self):
        self.assertEqual(prime_sum(10), 129)

if __name__ == '__main__':
    unittest.main()