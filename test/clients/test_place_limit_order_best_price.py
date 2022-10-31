from nova.clients.clients import clients
from decouple import config


def asserts_place_limit_order_best_price(
    exchange: str,
    pair: str,
    side: str,
    quantity: float,
    reduce_only: bool,
):

    client = clients(
        exchange=exchange,
        key=config(f"{exchange}TestAPIKey"),
        secret=config(f"{exchange}TestAPISecret"),
        testnet=True
    )

    is_posted, data = client.place_limit_order_best_price(
        pair=pair,
        side=side,
        quantity=quantity,
        reduce_only=reduce_only
    )

    if is_posted:

        std_output = ['time', 'order_id', 'pair', 'status', 'type', 'time_in_force', 'reduce_only', 'side',
                      'price', 'original_quantity', 'executed_quantity', 'executed_price']

        assert set(std_output).issubset(list(data.keys()))
        assert data['type'] == 'LIMIT'
        assert data['pair'] == pair
        assert data['original_quantity'] == quantity
        assert data['executed_quantity'] == 0

        client.cancel_order(pair=pair, order_id=data['order_id'])

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

    print(f"Test place_limit_order_best_price for {exchange.upper()} successful")


def test_place_limit_order_best_price():
    all_tests = [
        {
            'exchange': 'binance',
            'pair': 'BTCUSDT',
            'side': 'BUY',
            'quantity': 0.01,
            'reduce_only': False,
        },
        {
            'exchange': 'bybit',
            'pair': 'BTCUSDT',
            'side': 'BUY',
            'quantity': 0.01,
            'reduce_only': False,

        }
    ]

    for _test in all_tests:
        asserts_place_limit_order_best_price(
            exchange=_test['exchange'],
            pair=_test['pair'],
            side=_test['side'],
            quantity=_test['quantity'],
            reduce_only=_test['reduce_only']
        )


# test_place_limit_order_best_price()

exchange = 'ftx'

client = clients(
    exchange=exchange,
    key=config(f"{exchange}TestAPIKey"),
    secret=config(f"{exchange}TestAPISecret"),
    testnet=True
)

posted, data = client.place_limit_order_best_price(
    pair='BTC-PERP',
    side='BUY',
    quantity=0.001,
    reduce_only=False
)
#
# order_data = client.get_order(
#     pair="BTC-PERP",
#     order_id=193848819865
# )
