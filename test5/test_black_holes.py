import unittest
from black_holes import compute_evaporation_time

class TestBlackHoles(unittest.TestCase):
    def test_human_mass(self):
        # Test a black hole with the same mass as a human
        mass = 70  # kg
        expected_time = 2.61e+67  # seconds
        self.assertAlmostEqual(compute_evaporation_time(mass), expected_time)

    def test_moon_mass(self):
        # Test a black hole with the same mass as the Moon
        mass = 7.34e+22  # kg
        expected_time = 3.31e+47  # seconds
        self.assertAlmostEqual(compute_evaporation_time(mass), expected_time)

    def test_earth_mass(self):
        # Test a black hole with the same mass as the Earth
        mass = 5.97e+24  # kg
        expected_time = 2.51e+67  # seconds
        self.assertAlmostEqual(compute_evaporation_time(mass), expected_time)

    def test_sun_mass(self):
        # Test a black hole with the same mass as the Sun
        mass = 1.99e+30  # kg
        expected_time = 2.10e+67  # seconds
        self.assertAlmostEqual(compute_evaporation_time(mass), expected_time)

if __name__ == '__main__':
    unittest.main()
