from nova.clients.clients import clients
from decouple import config


def test_get_earliest_timestamp(exchange: str, pair: str, interval: str):

    client = clients(
        exchange=exchange,
        key=config(f"{exchange}TestAPIKey"),
        secret=config(f"{exchange}TestAPISecret"),
    )

    data = client._get_earliest_timestamp(
        pair=pair,
        interval=interval
    )

    assert len(str(data)) == 13

    print(f"Test _get_earliest_timestamp for {exchange.upper()} successful")


test_get_earliest_timestamp('binance', 'BTCUSDT', '1d')
