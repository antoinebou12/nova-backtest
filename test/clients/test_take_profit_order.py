from nova.clients.clients import clients
from decouple import config


def test_take_profit_order(exchange: str, pair: str, side: str, quantity: float):

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

    tp_data = client.take_profit_order(
        pair=pair,
        side='SELL',
        quantity=open_data['quantity'],
        tp_price=open_data['price'] * 1.01
    )

    return open_data, tp_data, client.get_exchange_info()


_pair = "BTCUSDT"
_side = "BUY"
_quantity = 0.001

_open, _tp, exchange_info = test_take_profit_order('binance', _pair, _side, _quantity)

for x in exchange_info['symbols']:
    if x['symbol'] == 'BTCUSDT':
        print(x)
