from nova.clients.clients import clients
from decouple import config
import time
from datetime import datetime


def assert_get_earliest_timestamp(exchange: str, pair: str, interval: str):

    client = clients(
        exchange=exchange,
        key=config(f"{exchange}TestAPIKey"),
        secret=config(f"{exchange}TestAPISecret"),
    )

    data = client._get_earliest_timestamp(
        pair=pair,
        interval=interval
    )

    server_date = datetime.utcfromtimestamp(data//1000)

    assert len(str(data)) == 13
    assert data < int(time.time() * 1000)

    print(f"Earliest Date: {server_date} -- Timestamp (ms): {data}")
    print(f"Test _get_earliest_timestamp for {exchange.upper()} successful")


def test_get_earliest_timestamp():

    all_test = [
        {
            'exchange': 'binance',
            'pair': 'BTCUSDT',
            'interval': '1d'
        },
        {
            'exchange': 'bybit',
            'pair': 'BTCUSDT',
            'interval': '1d'
        },
        {
            'exchange': 'ftx',
            'pair': 'BTC-PERP',
            'interval': '1d'
        },
        {
            'exchange': 'okx',
            'pair': 'BTC-USDT',
            'interval': '1d'
        },
        {
            'exchange': 'kucoin',
            'pair': 'XNTUSDTM',
            'interval': '1d'
        }
    ]

    for _test in all_test:

        assert_get_earliest_timestamp(
            exchange=_test['exchange'],
            pair=_test['pair'],
            interval=_test['interval']
        )


test_get_earliest_timestamp()
