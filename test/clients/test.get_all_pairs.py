from nova.clients.clients import clients
from decouple import config


def test_all_pairs(exchange: str):
    client = clients(
        exchange=exchange,
        key=config(f"{exchange}APIKey"),
        secret=config(f"{exchange}APISecret"),
    )

    all_pairs = client.get_all_pairs()

    unique_list = list(dict.fromkeys(all_pairs))
    assert all_pairs == unique_list
    assert type(all_pairs) == list

    print(f"Test get_all_pairs for {exchange.upper()} successful")


for _exchange in ['binance', 'ftx']:
    test_all_pairs(_exchange)

