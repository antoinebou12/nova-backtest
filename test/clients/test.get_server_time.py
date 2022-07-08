from nova.clients.clients import clients
from decouple import config
import time


def test_get_server_time(exchange: str):

    client = clients(
        exchange=exchange,
        key=config(f"{exchange}APIKey"),
        secret=config(f"{exchange}APISecret"),
    )

    server_time = client.get_server_time()

    min_dif = (time.time() - 1) * 1000
    max_dif = (time.time() + 1) * 1000
    assert type(server_time) == int
    assert (server_time > min_dif) and (server_time < max_dif)

    print(f"Test get_server_time for {exchange.upper()} successful")


for _exchange in ['binance', 'ftx']:
    test_get_server_time(_exchange)




