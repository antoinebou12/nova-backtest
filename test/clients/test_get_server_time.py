from nova.clients.clients import clients
from decouple import config
import time
from datetime import datetime


def asserts_get_server_time(exchange: str):

    client = clients(
        exchange=exchange,
        key=config(f"{exchange}TestAPIKey"),
        secret=config(f"{exchange}TestAPISecret"),
        testnet=True
    )

    server_time = client.get_server_time()

    min_dif = (time.time() - 1) * 1000
    max_dif = (time.time() + 1) * 1000

    assert type(server_time) == int
    assert (server_time > min_dif) and (server_time < max_dif)
    assert len(str(server_time)) == 13

    print(f"Test get_server_time for {exchange.upper()} successful")


def test_get_server_time():
    for _exchange in ['binance', 'bybit', 'ftx', 'kraken', 'kucoin']:
        asserts_get_server_time(_exchange)

#
# test_get_server_time()
#

exchange = 'coinbase'

client = clients(
    exchange=exchange,
    key=config(f"{exchange}TestAPIKey"),
    secret=config(f"{exchange}TestAPISecret"),
    passphrase=config(f"{exchange}TestPassPhrase"),
    testnet=True
)

data = client.setup_account(
    quote_asset='USD',
    leverage=2,
    list_pairs=['BTC-USD'],
    bankroll=5000,
    max_down=0.2
)



# data = client._get_candles(
#     pair='BTC-USD',
#     interval='1h',
#     start_time=int(datetime(2021, 1, 1).timestamp() * 1000),
#     end_time=int(datetime(2021, 1, 2).timestamp() * 1000),
# )


