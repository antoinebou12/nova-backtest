from nova.clients.clients import clients
from decouple import config


def asserts_get_order_book(exchange: str, pair: str):

    client = clients(
        exchange=exchange,
        key=config(f"{exchange}TestAPIKey"),
        secret=config(f"{exchange}TestAPISecret"),
        passphrase=config(f"{exchange}TestPassPhrase"),
        testnet=True
    )

    data = client.get_order_book(
        pair=pair,
    )

    for key, values in data.items():
        assert key in ['bids', 'asks']
        assert isinstance(values, list)

        for _value in values:

            assert isinstance(_value['price'], float)
            assert isinstance(_value['size'], float)

    print(f"Test get_order for {exchange.upper()} successful")


def test_get_order_book():
    all_tests = [
        # {
        #     'exchange': 'binance',
        #     'pair': 'BTCUSDT'
        # },
        # {
        #     'exchange': 'bybit',
        #     'pair': 'BTCUSDT'
        # },
        # {
        #     'exchange': 'ftx',
        #     'pair': 'BTC-PERP'
        # },
        # {
        #     'exchange': 'okx',
        #     'pair': 'BTC-USDT'
        # },
        {
            'exchange': 'kucoin',
            'pair': 'XBTUSDTM'
        },
    ]

    for _test in all_tests:

        asserts_get_order_book(
            exchange=_test['exchange'],
            pair=_test['pair']
        )


test_get_order_book()


