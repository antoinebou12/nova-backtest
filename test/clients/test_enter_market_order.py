from nova.clients.clients import clients
from decouple import config


def test_enter_market_order(exchange: str, pair: str, side: str, quantity: float):

    client = clients(
        exchange=exchange,
        key=config(f"{exchange}TestAPIKey"),
        secret=config(f"{exchange}TestAPISecret"),
        testnet=True
    )

    data = client.enter_market_order(
        pair=pair,
        side=side,
        quantity=quantity
    )

    print(data)


test_enter_market_order('binance', 'BTCUSDT', 'BUY', 0.002)



