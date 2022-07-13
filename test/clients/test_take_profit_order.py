from nova.clients.clients import clients
from decouple import config


def test_tp_sl_order(exchange: str, pair: str, side: str, quantity: float):

    client = clients(
        exchange=exchange,
        key=config(f"{exchange}APIKey"),
        secret=config(f"{exchange}APISecret"),
    )

    open_data = client.open_close_market_order(
        pair=pair,
        side=side,
        quantity=quantity
    )

    tp_data = client.tp_sl_order(
        pair=pair,
        side='SELL',
        quantity=open_data['quantity'],
        price=open_data['price'] * 1.015,
        tp_sl='tp'
    )

    sl_data = client.tp_sl_order(
        pair=pair,
        side='SELL',
        quantity=open_data['quantity'],
        price=open_data['price'] * 0.985,
        tp_sl='sl'
    )

    return open_data, tp_data, sl_data


_pair = "BTCUSDT"
_side = "BUY"
_quantity = 0.001

_open, _tp, _sl = test_tp_sl_order('binance', _pair, _side, _quantity)


