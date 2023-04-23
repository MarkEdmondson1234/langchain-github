from datetime import datetime

birth_date = datetime(1912, 6, 23, 0, 0)

test_dates = [
    datetime(2021, 1, 1, 0, 0),
    datetime(2021, 6, 23, 0, 0),
    datetime(2021, 12, 31, 23, 59)
]

for date in test_dates:
    days_since_birth = (date - birth_date).days
    print(f"There have been {days_since_birth} days since Alan Turing's birth on {birth_date.strftime('%Y-%m-%d')}.")
