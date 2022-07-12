from nova.clients.clients import clients
from decouple import config
import time


def test_get_prod_data(
        exchange: str,
        pair: str
):

    client = clients(
        exchange=exchange,
        key=config(f"{exchange}APIKey"),
        secret=config(f"{exchange}APISecret"),
    )

    min_time = int((time.time() - 2) * 1000)
    lat_price = client.get_last_price(pair)

    assert lat_price['pair_id'] == pair
    assert lat_price['price_timestamp'] > min_time


test_get_prod_data(exchange='binance', pair='BTCUSDT')

