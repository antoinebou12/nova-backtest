from datetime import datetime, timedelta
from typing import Optional, Dict
import dateparser
import time

import numpy as np
import pytz
import re


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


def compute_time_difference(
        start_time: Optional[int],
        end_time: Optional[int],
        unit: str
) -> Optional[float]:
    """

    Args:
        start_time: start time in timestamp millisecond
        end_time: start time in timestamp millisecond
        unit: can be 'second', 'minute', 'hour', 'day'

    Returns:

    """

    start_time_s = int(start_time / 1000)
    end_time_s = int(end_time / 1000)

    if unit == 'second':
        return end_time_s - start_time_s
    elif unit == 'minute':
        return (end_time_s - start_time_s) / 60
    elif unit == 'hour':
        return (end_time_s - start_time_s) / 3600
    elif unit == 'day':
        return (end_time_s - start_time_s) / (3600 * 24)


