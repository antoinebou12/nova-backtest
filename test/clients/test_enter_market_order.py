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


exchange = 'kucoin'

client = clients(
    exchange=exchange,
    key=config(f"{exchange}TestAPIKey"),
    secret=config(f"{exchange}TestAPISecret"),
    passphrase=config(f"{exchange}TestPassPhrase"),
    testnet=False
)





