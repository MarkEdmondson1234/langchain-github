import unittest
from datetime import datetime

class TestHowManyDays(unittest.TestCase):
    def test_how_many_days(self):
        birth_date = datetime(1912, 6, 23, 0, 0)
        test_dates = [
            datetime(2021, 1, 1, 0, 0),
            datetime(2021, 6, 23, 0, 0),
            datetime(2021, 12, 31, 23, 59)
        ]
        for date in test_dates:
            days_since_birth = (date - birth_date).days
            self.assertTrue(days_since_birth > 0)

if __name__ == '__main__':
    unittest.main()
