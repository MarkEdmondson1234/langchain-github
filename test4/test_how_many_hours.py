import unittest
from datetime import datetime
from how_many_hours import hours_since

class TestHoursSince(unittest.TestCase):
    def test_hours_since(self):
        # Test case 1: Test with a date in the past
        date_str = '2021-10-01:12:00'
        expected_hours = (datetime.now() - datetime.strptime(date_str, '%Y-%m-%d:%H:%M')).total_seconds() / 3600
        self.assertAlmostEqual(hours_since(date_str), expected_hours, places=2)

        # Test case 2: Test with a date in the future
        date_str = '2022-10-01:12:00'
        expected_hours = (datetime.now() - datetime.strptime(date_str, '%Y-%m-%d:%H:%M')).total_seconds() / 3600
        self.assertAlmostEqual(hours_since(date_str), expected_hours, places=2)

        # Test case 3: Test with the current date and time
        date_str = datetime.now().strftime('%Y-%m-%d:%H:%M')
        self.assertAlmostEqual(hours_since(date_str), 0, delta=0.1)

if __name__ == '__main__':
    unittest.main()