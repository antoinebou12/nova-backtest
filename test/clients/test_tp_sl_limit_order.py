from nova.clients.clients import clients
from decouple import config


def test_tp_sl_limit_order(exchange: str, pair: str, side: str, quantity: float):

    client = clients(
        exchange=exchange,
        key=config(f"{exchange}APIKey"),
        secret=config(f"{exchange}APISecret"),
    )

    data = client.open_close_market_order(
        pair=pair,
        side=side,
        quantity=quantity
    )

    tp_data = client.tp_sl_limit_order(
        pair=pair,
        side='SELL',
        quantity=quantity,
        price=data['price']*1.1,
        tp_sl='tp',
    )

    sl_data = client.tp_sl_limit_order(
        pair=pair,
        side='SELL',
        quantity=quantity,
        price=data['price'] * 0.9,
        tp_sl='sl',
    )



_pair = "BTCUSDT"
_side = "BUY"
_quantity = 0.001


test_tp_sl_limit_order('binance', _pair, _side, _quantity)
