from nova.clients.clients import clients
from decouple import config
import asyncio


def test_get_prod_data(
        exchange: str,
        list_pair: list,
        interval: str,
        nb_candles: int
):
    client = clients(
        exchange=exchange,
        key=config(f"{exchange}APIKey"),
        secret=config(f"{exchange}APISecret"),
    )

    data = asyncio.run(
        client.get_prod_data(
            list_pair=list_pair,
            interval=interval,
            nb_candles=nb_candles,
            current_state=None
        ))

    return data


_data = test_get_prod_data(
    exchange='binance',
    list_pair=['BTCUSDT', 'ETHUSDT'],
    interval='1h',
    nb_candles=100,
)


