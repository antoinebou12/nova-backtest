from nova.clients.clients import clients
from decouple import config
import time


def asserts_cancel_order(exchange: str, pair: str, type_pos: str, quantity: float):

    client = clients(
        exchange=exchange,
        key=config(f"{exchange}TestAPIKey"),
        secret=config(f"{exchange}TestAPISecret"),
        testnet=True
    )

    client.enter_market_order(
        pair=pair,
        type_pos=type_pos,
        quantity=quantity
    )

    exit_side = 'SELL' if type_pos == 'LONG' else 'BUY'

    upper = client.get_last_price(pair=pair)['latest_price'] * 1.1
    lower = client.get_last_price(pair=pair)['latest_price'] * 0.9

    tp_price = upper if type_pos == 'LONG' else lower

    tp_order = client.place_limit_tp(
        pair=pair,
        side=exit_side,
        quantity=quantity,
        tp_price=tp_price
    )

    tp = client.get_order(pair=pair, order_id=tp_order['order_id'])

    # Verify all information about TP d
    assert tp['status'] in ['NEW', "UNTRIGGERED"]

    client.cancel_order(
        pair=pair,
        order_id=tp_order['order_id']
    )

    cancel = client.get_order(pair=pair, order_id=tp_order['order_id'])

    assert isinstance(cancel, dict)
    assert cancel['status'] in ['CANCELED', 'DEACTIVATED']

    # Cancel the TP order that already been cancelled
    client.cancel_order(
        pair=pair,
        order_id=tp_order['order_id']
    )

    client.exit_market_order(
        pair=pair,
        type_pos=type_pos,
        quantity=quantity
    )

    print(f"Test cancel_order for {exchange.upper()} successful")


def test_cancel_order():

    all_tests = [
        {
            'exchange': 'binance',
            'pair': 'XRPUSDT',
            'type_pos': 'LONG',
            'quantity': 200
        },
        {
            'exchange': 'bybit',
            'pair': 'BTCUSDT',
            'type_pos': 'SHORT',
            'quantity': 0.1
        },

    ]

    for _test in all_tests:
        asserts_cancel_order(
            exchange=_test['exchange'],
            pair=_test['pair'],
            type_pos=_test['type_pos'],
            quantity=_test['quantity']
        )


# test_cancel_order()





exchange = 'ftx'

client = clients(
    exchange=exchange,
    key=config(f"{exchange}TestAPIKey"),
    secret=config(f"{exchange}TestAPISecret"),
    testnet=True
)

# market_data = client.enter_market_order(
#     pair="ETH-PERP",
#     type_pos="LONG",
#     quantity=0.01
# )


tp_data = client.place_limit_tp(
    pair="ETH-PERP",
    side="SELL",
    quantity=0.01,
    tp_price=1650
)


sl_data = client.place_market_sl(
    pair="ETH-PERP",
    side="SELL",
    quantity=0.01,
    sl_price=1400
)


client.cancel_order(
    pair="ETH-PERP",
    order_id=tp_data['order_id']
)

client.cancel_order(
    pair="ETH-PERP",
    order_id=sl_data['order_id']
)

