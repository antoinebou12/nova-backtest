from datetime import datetime, timedelta
from typing import Optional, Dict
import dateparser
import time
import pytz
import re


def date_to_milliseconds(date_str: str) -> int:
    """
    Note: Convert UTC date to milliseconds
    Args:
        date_str: date in readable format, i.e. "January 01, 2018", "11 hours ago UTC", "now UTC"
    Returns:
        timestamp in milliseconds
    """
    # get epoch value in UTC
    epoch: datetime = datetime.utcfromtimestamp(0).replace(tzinfo=pytz.utc)
    # parse our date string
    d: Optional[datetime] = dateparser.parse(date_str, settings={'TIMEZONE': "UTC"})
    if not d:
        raise "Error - date_to_milliseconds"

    # if the date is not timezone aware apply UTC timezone
    if d.tzinfo is None or d.tzinfo.utcoffset(d) is None:
        d = d.replace(tzinfo=pytz.utc)

    # return the difference in time
    return int((d - epoch).total_seconds() * 1000.0)


def interval_to_milliseconds(interval: str) -> Optional[int]:
    """Convert a Binance interval string to milliseconds
    Args:
        interval: interval string, e.g.: 1m, 3m, 5m, 15m, 30m, 1h, 2h, 4h, 6h, 8h, 12h, 1d, 3d, 1w
    Returns:
         int value of interval in milliseconds
         None if interval prefix is not a decimal integer
         None if interval suffix is not one of m, h, d, w
    """
    seconds_per_unit: Dict[str, int] = {
        "m": 60,
        "h": 60 * 60,
        "d": 24 * 60 * 60,
        "w": 7 * 24 * 60 * 60,
    }
    try:
        return int(interval[:-1]) * seconds_per_unit[interval[-1]] * 1000
    except (ValueError, KeyError):
        return None


def limit_to_start_date(interval: str, nb_candles: int):
    """
    Note: the number of candle is determine with the "now" timestamp
    Args:
        interval: interval string, e.g.: 1m, 3m, 5m, 15m, 30m, 1h, 2h, 4h, 6h, 8h, 12h, 1d, 3d, 1w
        nb_candles: number of candles needed.
    Returns:
        the start_time timestamp in milliseconds for production data
    """
    number_of_milliseconds = interval_to_milliseconds(interval)
    now_timestamp = int(time.time() * 1000)
    return now_timestamp - (nb_candles + 1) * number_of_milliseconds


def get_timedelta_unit(interval: str) -> timedelta:
    """
    Returns: a tuple that contains the unit and the multiplier needed to extract the data
    """
    multi = int(float(re.findall(r'\d+', interval)[0]))

    if 'm' in interval:
        return timedelta(minutes=multi)
    elif 'h' in interval:
        return timedelta(hours=multi)
    elif 'd' in interval:
        return timedelta(days=multi)


def is_opening_candle(interval: str):
    multi = int(float(re.findall(r'\d+', interval)[0]))
    unit = interval[-1]

    if multi == 1:
        if unit == 'm':
            return datetime.utcnow().second == 0
        elif unit == 'h':
            return datetime.utcnow().minute == 0
        elif unit == 'd':
            return datetime.utcnow().hour == 0
    else:
        if unit == 'm':
            return datetime.utcnow().minute % multi == 0
        elif unit == 'h':
            return datetime.utcnow().hour % multi == 0


def convert_ts_str(ts_str):
    """
    Args:
        ts_str:

    Returns:
    """
    if ts_str is None:
        return ts_str
    if type(ts_str) == int:
        return ts_str
    return date_to_milliseconds(ts_str)
