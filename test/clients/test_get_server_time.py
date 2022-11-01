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

exchange = 'kucoin'

client = clients(
    exchange=exchange,
    key=config(f"{exchange}TestAPIKey"),
    secret=config(f"{exchange}TestAPISecret"),
    passphrase=config(f"{exchange}TestPassPhrase"),
    testnet=True
)

# data = client.setup_account(
#     quote_asset='USDT',
#     leverage=2,
#     bankroll=500,
#     max_down=0.2,
#     list_pairs=['XBTUSDTM']
# )
#
#
data = client.enter_market_order(
    pair='ETHUSDTM',
    type_pos="LONG",
    quantity=1
)

data_two = client.enter_market_order(
    pair='XBTUSDTM',
    type_pos="LONG",
    quantity=10
)


data_three = client.enter_market_order(
    pair='ADAUSDTM',
    type_pos="LONG",
    quantity=10
)

# data = client._get_candles(
#     pair='BTC-USDT',
#     interval='1d',
#     start_time=int(datetime(2018, 3, 20).timestamp() * 1000),
#     end_time=int(datetime(2022, 3, 30).timestamp() * 1000)
# )

# #
# data = client._get_earliest_timestamp(
#     pair='XBTUSDTM',
#     interval='1h'
# )

#
# df = client._format_data(data)
#

#
# data = client.get_historical_data(
#     pair='XBTUSDTM',
#     interval='1h',
#     start_ts=int(datetime(2018, 1, 1).timestamp() * 1000),
#     end_ts=int(datetime(2022, 1, 1).timestamp() * 1000)
# )
#
