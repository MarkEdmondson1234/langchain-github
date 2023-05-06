import unittest
from black_holes import compute_evaporation_time

class TestBlackHoles(unittest.TestCase):

    def test_earth_mass(self):
        # Test a black hole with the same mass as the Earth
        mass = 1.98900e+30  # kg 
        expected_time = 1.15975e+67  # years 
        self.assertAlmostEqual(compute_evaporation_time(mass), expected_time)

if __name__ == '__main__':
    unittest.main()
