from nova.clients.clients import clients
from decouple import config


def asserts_cancel_pair_order(exchange: str, pair: str, type_pos: str, quantity: float):

    client = clients(
        exchange=exchange,
        key=config(f"{exchange}APIKey"),
        secret=config(f"{exchange}APISecret"),
    )

    data = client.enter_market_order(
        pair=pair,
        type_pos=type_pos,
        quantity=quantity
    )

    print(data)


def test_cancel_pair_order():

    all_Tests = [
        {
            'exchange': 'binance',
            'pair': 'BTCUSDT',
            'type_pos': 'LONG',
            'quantity': ''
        }
    ]

_pair = "BTCUSDT"
_side = "BUY"
_quantity = 0.001

test_cancel_pair_order('binance', _pair, _side, _quantity)
