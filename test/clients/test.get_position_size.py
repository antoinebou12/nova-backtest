from nova.clients.clients import clients
from decouple import config


def test_get_position_size(
        exchange: str,
        based_asset: str
):

    client = clients(
        exchange=exchange,
        key=config(f"{exchange}APIKey"),
        secret=config(f"{exchange}APISecret"),
    )

    balances = client.get_balance()
    base_balance_info = None
    for balance in balances:
        if balance['asset'] == based_asset:
            base_balance_info = balance

    print(base_balance_info)

    size_amount_1 = client.get_position_size(
        based_asset=based_asset,
        leverage=4,
        position_size=1/10,
        bankroll=500,
        current_pnl=0,
        current_positions_amt=450,
        geometric_size=True
    )

    assert size_amount_1 == 50


_based_asset = 'USDT'
test_get_position_size(
    exchange='binance',
    based_asset=_based_asset,
)
