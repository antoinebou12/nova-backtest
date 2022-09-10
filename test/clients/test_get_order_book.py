from nova.clients.clients import clients
from decouple import config


def test_get_order_book(exchange: str, pair: str):

    client = clients(
        exchange=exchange,
        key=config(f"{exchange}TestAPIKey"),
        secret=config(f"{exchange}TestAPISecret"),
        testnet=True
    )

    data = client.get_order_book(
        pair=pair,
    )

    print(data)


test_get_order_book('binance', 'BTCUSDT')


