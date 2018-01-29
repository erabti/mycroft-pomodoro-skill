from datetime import datetime, timedelta
import time
import dateutil.parser as dparser

def parse_to_datetime(duration, timeleft=False):
    """ Takes in duration and output datetime

        Args:
            duration (str): string in any time format
                            ex. 1 hour 2 minutes 30 seconds

        Return:
            timer_time (datetime): datetime object with
                                   time now + duration
    """
    parsed_time = dparser.parse(duration, fuzzy=True)
    now = datetime.now()

    seconds = parsed_time.second
    minutes = parsed_time.minute
    hours = parsed_time.hour

    timer_time = now + timedelta(hours=hours, minutes=minutes, seconds=seconds)
    time_left = timedelta(hours=hours, minutes=minutes, seconds=seconds)
    if timeleft:
        return time_left
    else:
	return timer_time
print(int(timedelta(0)))
