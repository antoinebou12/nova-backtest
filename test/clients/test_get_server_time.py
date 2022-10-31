from nova.clients.clients import clients
from decouple import config
import time


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
    for _exchange in ['binance', 'bybit', 'ftx', 'kraken']:
        asserts_get_server_time(_exchange)


# test_get_server_time()


exchange = 'kraken'

client = clients(
    exchange=exchange,
    key=config(f"{exchange}TestAPIKey"),
    secret=config(f"{exchange}TestAPISecret"),
    testnet=True
)


# positions = client.get_actual_positions(pairs=['pf_xbtusd'])
positions = client.setup_account(
    quote_asset='USD',
    leverage=5,
    bankroll=2000,
    max_down=0.2,
    list_pairs=['pf_xbtusd', 'pf_ethusd', 'pf_atomusd']
)

# for key, value in positions.items():
#     print(f'########### {key}')
#     print(value)

