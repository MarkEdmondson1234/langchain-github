

#NOCODEERROR: Test failed due to an error not associated with the code

def hours_since_now(date):
    from datetime import datetime
    date_format = "%Y-%m-%d %H:%M"
    now = datetime.now()
    given_date = datetime.strptime(date, date_format)
    diff = now - given_date
    return diff.total_seconds() // 3600