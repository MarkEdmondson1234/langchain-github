import unittest
import how_many_hours

class TestHowManyHours(unittest.TestCase):
    def test_hours_since_now(self):
        self.assertEqual(how_many_hours.hours_since_now('2020-01-01 00:00'), 744)
        self.assertEqual(how_many_hours.hours_since_now('2020-02-01 00:00'), 672)
        self.assertEqual(how_many_hours.hours_since_now('2020-03-01 00:00'), 600)
        self.assertEqual(how_many_hours.hours_since_now('2020-04-01 00:00'), 528)

if __name__ == '__main__':
    unittest.main()