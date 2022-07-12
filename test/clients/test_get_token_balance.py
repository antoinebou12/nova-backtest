from nova.clients.clients import clients
from decouple import config


def test_get_token_balance(
        exchange: str,
        based_asset: str
):

    client = clients(
        exchange=exchange,
        key=config(f"{exchange}APIKey"),
        secret=config(f"{exchange}APISecret"),
    )

    balances = client.get_token_balance(based_asset=based_asset)

    assert balances > 0


_based_asset = 'USDT'
test_get_token_balance(
    exchange='binance',
    based_asset=_based_asset,
)
