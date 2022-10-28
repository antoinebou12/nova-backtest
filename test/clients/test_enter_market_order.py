from nova.clients.clients import clients
from decouple import config


def asserts_enter_market_order(exchange: str, pair: str, type_pos: str, quantity: float):

    client = clients(
        exchange=exchange,
        key=config(f"{exchange}TestAPIKey"),
        secret=config(f"{exchange}TestAPISecret"),
        testnet=True
    )

    positions = client.get_actual_positions(
        pairs=pair
    )

    if len(positions) != 0:

        for _pair, _info in positions.items():

            client.exit_market_order(
                pair=_pair,
                type_pos=_info['type_pos'],
                quantity=_info['position_size']
            )

    order = client.enter_market_order(
        pair=pair,
        type_pos=type_pos,
        quantity=quantity
    )

    assert order['status'] in ['NEW', 'CREATED']

    side = 'BUY' if type_pos == 'LONG' else 'SELL'

    # get price
    latest_price = client.get_last_price(pair)['latest_price']
    q_precision = client.pairs_info[pair]['quantityPrecision']

    market_order = client.get_order(pair, order['order_id'])

    assert market_order['type'] == 'MARKET'
    assert market_order['status'] == 'FILLED'
    assert market_order['pair'] == pair
    assert not market_order['reduce_only']
    assert market_order['time_in_force'] in ['GTC', 'ImmediateOrCancel']
    assert market_order['side'] == side
    assert market_order['price'] == 0
    assert market_order['stop_price'] == 0
    assert market_order['original_quantity'] == round(quantity, q_precision)
    assert market_order['executed_quantity'] == round(quantity, q_precision)
    assert latest_price * 0.90 < market_order['executed_price'] < latest_price * 1.1

    client.exit_market_order(
        pair=pair,
        type_pos=type_pos,
        quantity=quantity
    )

    print(f"Test enter_market_order {type_pos} for {exchange.upper()} successful")


def test_enter_market_order():

    all_tests = [
        # {
        #     'exchange': 'binance',
        #     'pair': 'BTCUSDT',
        #     'type_pos': 'LONG',
        #     'quantity': 0.01
        # },
        {
            'exchange': 'bybit',
            'pair': 'BTCUSDT',
            'type_pos': 'LONG',
            'quantity': 0.01
        },
        {
            'exchange': 'bybit',
            'pair': 'BTCUSDT',
            'type_pos': 'SHORT',
            'quantity': 0.01
        }
    ]

    for _test in all_tests:

        asserts_enter_market_order(
            exchange=_test['exchange'],
            pair=_test['pair'],
            type_pos=_test['type_pos'],
            quantity=_test['quantity']
        )


# test_enter_market_order()


exchange = 'kraken'

client = clients(
    exchange=exchange,
    key=config(f"{exchange}TestAPIKey"),
    secret=config(f"{exchange}TestAPISecret"),
    testnet=True
)

entry_data = client.enter_market_order(
    pair="pf_xbtusd",
    type_pos="LONG",
    quantity=0.1
)

exit_data = client.exit_market_order(
    pair="pf_xbtusd",
    type_pos="LONG",
    quantity=0.1
)

# order_data = client.get_order(
#     pair="pf_xbtusd",
#     order_id=entry_data['order_id']
# )

cancel_order = client.cancel_order(
    pair="pf_xbtusd",
    order_id=entry_data['order_id']
)

# order_data = client.get_order_trades(
#     pair="ETH-PERP",
#     order_id=193550433909
# )


# for trade in order_data:
#     print(trade)

#
# returned_data = {'id': 193550433909, 'clientId': None, 'market': 'ETH-PERP', 'type': 'market', 'side': 'buy',
#                  'price': None, 'size': 0.01, 'status': 'new', 'filledSize': 0.0, 'remainingSize': 0.01,
#                  'reduceOnly': False, 'liquidation': None, 'avgFillPrice': None, 'postOnly': False, 'ioc': True,
#                  'createdAt': '2022-10-26T02:32:10.695169+00:00', 'future': 'ETH-PERP'
#                  }
