
from nova.clients.clients import clients
from decouple import config


def asserts_setup_account(
        exchange: str,
        quote_asset: str,
        leverage: int,
        list_pairs: list,
        bankroll: float,
        max_down: float
):

    client = clients(
        exchange=exchange,
        key=config(f"{exchange}TestAPIKey"),
        secret=config(f"{exchange}TestAPISecret"),
        passphrase=config(f"{exchange}TestPassPhrase"),
        testnet=False
    )

    client.setup_account(
        quote_asset=quote_asset,
        leverage=leverage,
        list_pairs=list_pairs,
        bankroll=bankroll,
        max_down=max_down
    )

    print(f"Test setup_account for {exchange.upper()} successful")


def test_setup_account():

    all_tests = [
        # {
        #     'exchange': 'binance',
        #     'quote_asset': 'USDT',
        #     'leverage': 2,
        #     'list_pairs': ['BTCUSDT', 'ETHUSDT'],
        #     'bankroll': 1000,
        #     'max_down': 0.3
        # },
        # {
        #     'exchange': 'bybit',
        #     'quote_asset': 'USDT',
        #     'leverage': 2,
        #     'list_pairs': ['BTCUSDT', 'ETHUSDT'],
        #     'bankroll': 1000,
        #     'max_down': 0.3
        # },
        # {
        #     'exchange': 'ftx',
        #     'quote_asset': 'USD',
        #     'leverage': 5,
        #     'list_pairs': ['BTC-PERP', 'ETH-PERP'],
        #     'bankroll': 50,
        #     'max_down': 0.2
        # },
        # {
        #     'exchange': 'okx',
        #     'quote_asset': 'USDT',
        #     'leverage': 5,
        #     'list_pairs': ['BTC-USDT', 'ETH-USDT'],
        #     'bankroll': 50,
        #     'max_down': 0.2
        # },
        {
            'exchange': 'kucoin',
            'quote_asset': 'USDT',
            'leverage': 5,
            'list_pairs': ['XBTUSDTM', 'ETHUSDTM'],
            'bankroll': 50,
            'max_down': 0.2
        }
    ]

    for _test in all_tests:

        asserts_setup_account(
            exchange=_test['exchange'],
            quote_asset=_test['quote_asset'],
            leverage=_test['leverage'],
            list_pairs=_test['list_pairs'],
            bankroll=_test['bankroll'],
            max_down=_test['max_down']
        )


test_setup_account()
