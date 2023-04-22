from datetime import datetime

def hours_since(date_str):
    date_time_obj = datetime.strptime(date_str, '%Y-%m-%d:%H:%M')
    time_diff = datetime.now() - date_time_obj
    hours_diff = time_diff.total_seconds() / 3600
    return round(hours_diff, 2)
