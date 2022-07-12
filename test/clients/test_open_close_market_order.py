from nova.clients.clients import clients
from decouple import config


def test_open_close_market_order(exchange: str, pair: str, side: str, quantity: float):

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

    assert data['pair'] == pair
    assert data['is_buyer']
    assert data['quantity'] == quantity
    assert data['tx_fee_in_based_asset'] > 0
    assert data['tx_fee_in_other_asset']['BNB'] > 0


_pair = "BTCUSDT"
_side = "BUY"
_quantity = 0.001

test_open_close_market_order('binance', _pair, _side, _quantity)



