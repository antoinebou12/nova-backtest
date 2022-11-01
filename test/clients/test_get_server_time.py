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
    key=config(f"{exchange}APIKey"),
    secret=config(f"{exchange}APISecret"),
    passphrase=config(f"{exchange}PassPhrase"),
    testnet=False
)

# data = client.get_order_book(pair='BTC-USD')

# data = client.get_last_price(pair='BTC-USD')
#
entry_ = client.enter_market_order(
    pair='BTC-USD',
    type_pos='LONG',
    quantity=0.2
)


tp_order = client.place_limit_tp(
    pair='BTC-USD',
    side='SELL',
    quantity=0.2,
    tp_price=25000
)

sl_order = client.place_market_sl(
    pair='BTC-USD',
    side='SELL',
    quantity=0.1,
    sl_price=18000
)


# exit_ = client.exit_market_order(
#     pair='BTC-USD',
#     type_pos='LONG',
#     quantity=0.1
# )
#
# order_ = client.get_order(
#     pair='BTC-USD',
#     order_id='398a65b0-fabf-4190-b8fb-9b4d218587e7'
# )

# trades_ = client.get_order_trades(
#     pair='BTC-USD',
#     order_id='e6f460f4-d5c0-4e46-80f3-8e7c91078e97'
# )

# data = client._get_candles(
#     pair='BTC-USD',
#     interval='1h',
#     start_time=int(datetime(2021, 1, 1).timestamp() * 1000),
#     end_time=int(datetime(2021, 1, 2).timestamp() * 1000),
# )

