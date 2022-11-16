from nova.random.backtest import RANDOM_BACKTEST


def asserts_get_list_pair(exchange: str, list_pair: list, quote_asset: str):
    
    _rand_ = RANDOM_BACKTEST(
        exchange=exchange,
        list_pair=list_pair,
        quote_asset=quote_asset
    )

    assert _rand_.list_pair

    
    


def test_get_list_pair():
    all_tests = [
        {
            'exchange': 'binance',
            'list_pair': None,
            'quote_asset': 'USDT'
        },
        {
            'exchange': 'binance',
            'list_pair': None,
            'quote_asset': 'USDT'
        }
    ]

    for test in all_tests:
        asserts_get_list_pair(
            exchange=test['exchange'],
            list_pair=test['list_pair'],
            quote_asset=test['quote_asset']
        )

test_get_list_pair()