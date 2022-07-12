from nova.clients.clients import clients
from decouple import config


def test_open_close_order(exchange):

    client = clients(
        exchange=exchange,
        key=config(f"{exchange}APIKey"),
        secret=config(f"{exchange}APISecret"),
    )





_pair = "BTCUSDT"
_side = "BUY"
_quantity = 0.000731

response = client.open_position_order(
    pair=_pair,
    side=_side,
    quantity=_quantity
)
