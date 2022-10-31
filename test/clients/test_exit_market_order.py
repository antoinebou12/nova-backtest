from nova.clients.clients import clients
from decouple import config


def asserts_exit_market_order(exchange: str, pair: str, type_pos: str, quantity: float):

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

    client.enter_market_order(
        pair=pair,
        type_pos=type_pos,
        quantity=quantity
    )

    exit_side = 'SELL' if type_pos == 'LONG' else 'BUY'

    market_exit = client.exit_market_order(
        pair=pair,
        type_pos=type_pos,
        quantity=quantity
    )

    assert market_exit['type'] == 'MARKET'
    assert market_exit['status'] in ['FILLED', 'CREATED']
    assert market_exit['pair'] == pair
    assert market_exit['reduce_only']
    assert market_exit['side'] == exit_side
    assert market_exit['original_quantity'] == quantity
    assert market_exit['executed_quantity'] == quantity

    print(f"Test exit_market_order for {exchange.upper()} successful")


def test_exit_market_order():

    all_tests = [
        {
            'exchange': 'binance',
            'pair': 'BTCUSDT',
            'type_pos': 'LONG',
            'quantity': 0.01
        },
        {
            'exchange': 'bybit',
            'pair': 'BTCUSDT',
            'type_pos': 'LONG',
            'quantity': 0.01
        }
    ]

    for _test in all_tests:

        asserts_exit_market_order(
            exchange=_test['exchange'],
            pair=_test['pair'],
            type_pos=_test['type_pos'],
            quantity=_test['quantity']
        )


# test_exit_market_order()


exchange = 'ftx'

client = clients(
    exchange=exchange,
    key=config(f"{exchange}TestAPIKey"),
    secret=config(f"{exchange}TestAPISecret"),
    testnet=True
)

# data = client.exit_market_order(
#     pair="ETH-PERP",
#     type_pos="LONG",
#     quantity=0.01
# )

order_data = client.get_order(
    pair="ETH-PERP",
    order_id=193679239035
)

{'id': 193679239035, 'clientId': None, 'market': 'ETH-PERP', 'type': 'market', 'side': 'sell', 'price': None,
 'size': 0.01, 'status': 'new', 'filledSize': 0.0, 'remainingSize': 0.01, 'reduceOnly': True, 'liquidation': None,
 'avgFillPrice': None, 'postOnly': False, 'ioc': True, 'createdAt': '2022-10-26T11:19:22.196390+00:00',
 'future': 'ETH-PERP'}
