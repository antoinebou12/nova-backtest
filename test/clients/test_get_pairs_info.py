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

        assert isinstance(value['quote_asset'], str)

        assert isinstance(value['maxQuantity'], float)
        assert value['maxQuantity'] > 0
        assert isinstance(value['minQuantity'], float)
        assert value['minQuantity'] > 0
        assert isinstance(value['tick_size'], float)
        assert value['tick_size'] > 0
        assert isinstance(value['pricePrecision'], int)
        assert value['pricePrecision'] >= 0
        assert isinstance(value['step_size'], float)
        assert value['step_size'] > 0
        assert isinstance(value['quantityPrecision'], int)
        assert value['quantityPrecision'] >= 0

    print(f'Completed for {len(data)} pairs')

    print(f"Test get_pairs_info for {exchange.upper()} successful")


def test_get_pairs_info():

    for exchange in ['binance', 'bybit', 'ftx', 'okx', 'kucoin']:
        asserts_get_pairs_info(exchange=exchange)


test_get_pairs_info()

