from nova.clients.clients import clients
from decouple import config


def asserts_enter_market_order(exchange: str, pair: str, type_pos: str, quantity: float):

    client = clients(
        exchange=exchange,
        key=config(f"{exchange}TestAPIKey"),
        secret=config(f"{exchange}TestAPISecret"),
        passphrase=config(f"{exchange}TestPassPhrase"),
        testnet=False
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
        #     'quantity': 0.001
        # },
        # {
        #     'exchange': 'bybit',
        #     'pair': 'BTCUSDT',
        #     'type_pos': 'LONG',
        #     'quantity': 0.001
        # },
        {
            'exchange': 'bybit',
            'pair': 'BTCUSDT',
            'type_pos': 'SHORT',
            'quantity': 0.001
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


exchange = 'okx'

client = clients(
    exchange=exchange,
    key=config(f"{exchange}TestAPIKey"),
    secret=config(f"{exchange}TestAPISecret"),
    passphrase=config(f"{exchange}TestPassPhrase"),
    testnet=False
)


# enter_limit = client.place_limit_order_best_price(
#     pair='BTC-USDT',
#     side="BUY",
#     quantity=0.001,
#     reduce_only=False
# )


# enter_limit_loop = client._looping_limit_orders(
#     pair='BTC-USDT',
#     side="BUY",
#     quantity=0.001,
#     reduce_only=False,
#     duration=60
# )


# enter_limit_loop = client._enter_limit_then_market(
#     pair='ETH-USDT',
#     type_pos="LONG",
#     quantity=0.01,
#     sl_price=1550,
#     tp_price=1700
# )

# enter_long = client.enter_market_order(
#     pair='BTC-USDT',
#     type_pos="LONG",
#     quantity=0.001
# )

# enter_short = client.enter_market_order(
#     pair='ETH-USDT',
#     type_pos="SHORT",
#     quantity=0.01
# )

#
# exit_long = client.exit_market_order(
#     pair='BTC-USDT',
#     type_pos="LONG",
#     quantity=0.001
# )

# exit_short = client.exit_market_order(
#     pair='ETH-USDT',
#     type_pos="SHORT",
#     quantity=0.01
# )
#
#
# place_limit_tp = client.place_limit_tp(
#     pair='BTC-USDT',
#     side="SELL",
#     quantity=0.001,
#     tp_price=21360
# )
#
#


# tp_order = client.get_order(pair='BTC-USDT', order_id='508910380719161349')
# sl_order = client.get_order(pair='BTC-USDT', order_id='508910412591677440')


# enter_short = client.enter_market_order(
#     pair='ETH-USDT',
#     type_pos="SHORT",
#     quantity=0.01
# )

#
# exit_long = client.exit_market_order(
#     pair='BTC-USDT',
#     type_pos="LONG",
#     quantity=0.001
# )

# exit_short = client.exit_market_order(
#     pair='ETH-USDT',
#     type_pos="SHORT",
#     quantity=0.01
# )
#

# place_limit_tp = client.place_limit_tp(
#     pair='BTC-USDT',
#     side="SELL",
#     quantity=0.001,
#     tp_price=21160
# )

# place_market_sl = client.place_market_sl(
#     pair='BTC-USDT',
#     side="SELL",
#     quantity=0.001,
#     sl_price=21140
# )
#

# tp_order = client.get_order(pair='BTC-USDT', order_id='508910380719161349')
# sl_order = client.get_order(pair='BTC-USDT', order_id='508910412591677440')

