from nova.clients.clients import clients
from decouple import config


def assert_get_token_balance(
        exchange: str,
        quote_asset: str
):

    client = clients(
        exchange=exchange,
        key=config(f"{exchange}TestAPIKey"),
        secret=config(f"{exchange}TestAPISecret"),
        testnet=True
    )

    balances = client.get_token_balance(quote_asset=quote_asset)

    assert isinstance(balances, float)
    assert balances >= 0

    print(f"Test get_token_balance for {exchange.upper()} successful")


def test_get_token_balance():
    all_tests = [
        {
            'exchange': 'binance',
            'quote_asset': 'USDT'
        },
        {
            'exchange': 'bybit',
            'quote_asset': 'USDT'
        }
    ]

    for _test in all_tests:
        assert_get_token_balance(
            exchange=_test['exchange'],
            quote_asset=_test['quote_asset']
        )


test_get_token_balance()
