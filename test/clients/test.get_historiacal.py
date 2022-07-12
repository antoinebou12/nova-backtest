import pandas as pd
from nova.clients.clients import clients
from nova.utils.helpers import date_to_milliseconds
from nova.utils.constant import DATA_FORMATING, STD_CANDLE_FORMAT

from decouple import config
from binance.client import Client
from datetime import datetime


def get_reference_data(interval, _start_time, _end_time, historical: bool):
    python_binance = Client(config("binanceAPIKey"), config("binanceAPISecret"))
    reference_data = python_binance.futures_historical_klines(
        "BTCUSDT",
        interval,
        _start_time,
        _end_time
    )

    df = pd.DataFrame(reference_data, columns=DATA_FORMATING['binance']['columns'])

    for var in DATA_FORMATING['binance']['num_var']:
        df[var] = pd.to_numeric(df[var], downcast="float")

    if historical:
        df = df[STD_CANDLE_FORMAT]
        df['next_open'] = df['open'].shift(-1)
        return df.dropna()
    else:
        df = df[STD_CANDLE_FORMAT]
        df['open_time_datetime'] = pd.to_datetime(df['open_time'], unit='ms')
        return df.dropna()


def test_get_historical(exchange: str, pair: str, interval: str, start_time: int, end_time: int):

    client = clients(
        exchange=exchange,
        key=config(f"{exchange}APIKey"),
        secret=config(f"{exchange}APISecret"),
    )

    rf_df = get_reference_data(interval, start_time, end_time, historical=True)

    df = client.get_historical(
        pair=pair,
        interval=interval,
        start_time=start_time,
        end_time=end_time
    )

    assert df.shape == rf_df.shape

    assert df.iloc[-1, 0] == rf_df.iloc[-1, 0]
    assert df.iloc[-1, -1] == rf_df.iloc[-1, -1]


_pair = "BTCUSDT"
_interval = "1h"
_start_time = date_to_milliseconds(datetime(2022, 1, 1).strftime('%d %b, %Y'))
_end_time = date_to_milliseconds(datetime(2022, 4, 1).strftime('%d %b, %Y'))


test_get_historical(
    exchange="binance",
    pair=_pair,
    interval=_interval,
    start_time=_start_time,
    end_time=_end_time
)

#
# _pair = "BTC-PERP"
# ftx_data = test_get_historical(
#     exchange="ftx",
#     pair=_pair,
#     interval=_interval,
#     start_time=start_timing,
#     end_time=end_timing
# )

