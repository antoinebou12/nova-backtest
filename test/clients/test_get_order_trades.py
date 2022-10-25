from nova.clients.clients import clients
from decouple import config
import time


def asserts_get_order_trades(exchange: str, pair: str, type_pos: str, quantity: float):

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

    market_order = client.enter_market_order(
        pair=pair,
        type_pos=type_pos,
        quantity=quantity
    )

    time.sleep(2)

    ot_data = client.get_order_trades(
        pair=pair,
        order_id=market_order['order_id']
    )

    for var in ['quote_asset', 'tx_fee_in_quote_asset', 'tx_fee_in_other_asset', 'nb_of_trades', 'is_buyer']:
        assert var in list(ot_data.keys())

    assert ot_data['quote_asset'] == 'USDT'
    assert ot_data['tx_fee_in_quote_asset'] > 0
    assert ot_data['nb_of_trades'] > 0
    assert ot_data['is_buyer'] if type_pos == 'LONG' else not ot_data['is_buyer']

    client.exit_market_order(
        pair=pair,
        type_pos=type_pos,
        quantity=quantity
    )

    print(f"Test get_order {type_pos} for {exchange.upper()} successful")


def test_get_order_trades():
    all_tests = [
        # {
        #     'exchange': 'binance',
        #     'pair': 'BTCUSDT',
        #     'type_pos': 'LONG',
        #     'quantity': 0.01
        # },
        # {
        #     'exchange': 'binance',
        #     'pair': 'BTCUSDT',
        #     'type_pos': 'SHORT',
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
        asserts_get_order_trades(
            exchange=_test['exchange'],
            pair=_test['pair'],
            type_pos=_test['type_pos'],
            quantity=_test['quantity']
        )


test_get_order_trades()
