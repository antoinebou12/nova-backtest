from nova.clients.binance import Binance
from nova.clients.ftx import FTX
from decouple import config

from binance.client import Client
from datetime import datetime
from nova.utils.constant import DATA_FORMATING


def test_get_historical(exchange: str, pair: str, interval: str, start_time: str, end_time: str):
    if exchange == "binance":
        client = Binance(key=config("BinanceAPIKey"), secret=config("BinanceAPISecret"))
    elif exchange == 'ftx':
        client = FTX(key=config("ftxAPIkey"), secret=config("ftxAPIsecret"))

    python_binance = Client(config("BinanceAPIKey"), config("BinanceAPISecret"))

    reference_data = python_binance.futures_historical_klines(
        "BTCUSDT",
        interval,
        start_time,
        end_time
    )

    data = client.get_historical(
        pair=pair,
        interval=interval,
        start_time=start_time,
        end_time=end_time
    )

    assert len(reference_data) == len(data)
    assert type(data) == list

    ref_timestamp = []

    for candle in reference_data:
        ref_timestamp.append(int(candle[0]))

    data_timestamp = []

    for candle in data:
        if exchange == 'binance':
            data_timestamp.append(int(candle[0]))
        elif exchange == 'ftx':
            data_timestamp.append(int(candle['time']))

    assert ref_timestamp == data_timestamp

    return data


_pair = "BTCUSDT"
_interval = "1h"
start_timing = datetime(2022, 1, 1).strftime('%d %b, %Y')
end_timing = datetime(2022, 4, 1).strftime('%d %b, %Y')

binance_data = test_get_historical(
    exchange="binance",
    pair=_pair,
    interval=_interval,
    start_time=start_timing,
    end_time=end_timing
)

_pair = "BTC-PERP"

ftx_data = test_get_historical(
    exchange="ftx",
    pair=_pair,
    interval=_interval,
    start_time=start_timing,
    end_time=end_timing
)

