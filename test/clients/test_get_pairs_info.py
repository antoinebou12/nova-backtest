from nova.clients.clients import clients
from decouple import config


def asserts_get_pairs_info(exchange: str):

    client = clients(
        exchange=exchange,
        key=config(f"{exchange}TestAPIKey"),
        secret=config(f"{exchange}TestAPISecret"),
        testnet=True
    )

    data = client.get_pairs_info()

    for key, value in data.items():

        assert type(key) == str
        assert type(value) == dict

        assert 'pricePrecision' in list(value.keys())
        assert 'quote_asset' in list(value.keys())
        assert 'quantityPrecision' in list(value.keys())
        assert 'maxQuantity' in list(value.keys())
        assert 'minQuantity' in list(value.keys())

    print(f"Test get_pairs_info for {exchange.upper()} successful")


def test_get_pairs_info():

    for exchange in ['binance', 'bybit', 'ftx', 'okx', 'kucoin']:
        asserts_get_pairs_info(exchange=exchange)


test_get_pairs_info()
