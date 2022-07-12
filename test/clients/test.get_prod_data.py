from nova.clients.clients import clients
from nova.utils.helpers import interval_to_milliseconds

from decouple import config
import time


def test_get_prod_data(
        exchange: str,
        pair: str, interval: str,
        nb_candles: int
):

    client = clients(
        exchange=exchange,
        key=config(f"{exchange}APIKey"),
        secret=config(f"{exchange}APISecret"),
    )

    data, late_time = client.get_prod_candles(pair, interval, nb_candles)
    current_time = (time.time()) * 1000
    minimum_end_time = current_time - interval_to_milliseconds(interval)

    assert len(data) == nb_candles
    assert (data.iloc[-1, 6] <= current_time) and (data.iloc[-1, 6] >= minimum_end_time)


_pair = "BTCUSDT"
_interval = "15m"
_nb_candles = 200

test_get_prod_data(exchange='binance', pair=_pair, interval=_interval, nb_candles=_nb_candles)




