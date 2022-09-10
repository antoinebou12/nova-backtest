from nova.clients.clients import clients
from decouple import config


def test_limit_order_best_price(exchange: str, pair: str, side: str, quantity: float, reduce_only: bool):

    client = clients(
        exchange=exchange,
        key=config(f"{exchange}TestAPIKey"),
        secret=config(f"{exchange}TestAPISecret"),
        testnet=True
    )

    data = client._limit_order_best_price(
        pair=pair,
        side=side,
        qty=quantity,
        reduce_only=reduce_only
    )

    print(data[0])
    print(data[1])


test_limit_order_best_price('binance', 'BTCUSDT', 'BUY', 0.002, False)
test_limit_order_best_price('binance', 'BTCUSDT', 'SELL', 0.002, True)


