from nova.api.client import NovaAPI
from decouple import config


def test_create_pair(value: str, name: str, fiat: str, strategies: list, exchanges: list):

    nova_client = NovaAPI(config('NovaAPISecret'))

    data = nova_client.create_pair(
        value=value,
        name=name,
        fiat=fiat,
        strategies=strategies,
        exchanges=exchanges
    )

    assert data['name'] == name
    assert data['value'] == value
    assert data['fiat'] == fiat
    assert data['pair'] == value + fiat


# test_create_pair(
#     value="BTC",
#     name="Bitcoin",
#     fiat="USDT",
#     strategies=[{"name": "vmc"}, {"name": "super_trend"}],
#     exchanges=['binance', 'ftx', 'bybit'],
# )
#
# test_create_pair(
#     value="ETH",
#     name="Ethereum",
#     fiat="USDT",
#     strategies=[{"name": "vmc"}, {"name": "super_trend"}],
#     exchanges=['binance', 'ftx', 'bybit'],
# )


def test_delete_pair(pair_id: str):

    nova_client = NovaAPI(config('NovaAPISecret'))

    is_true = nova_client.delete_pair(
        pair_id=pair_id
    )

    assert is_true['deletePair']

#
# test_delete_pair(pair_id="6345879384e8922219888321")
# test_delete_pair(pair_id="634588bd84e892221988832d")


def test_read_pairs(pair_id: str = None):

    nova_client = NovaAPI(config('NovaAPISecret'))

    data = nova_client.read_pairs(
        pair_id=pair_id
    )

    print(data)


test_read_pairs(pair_id="634588fd84e892221988833b")
# test_read_pairs()


def test_update_pair(_id: str, strategies: list, exchanges: list):

    nova_client = NovaAPI(config('NovaAPISecret'))

    data = nova_client.update_pair(
        pair_id=_id,
        strategies=strategies,
        exchanges=exchanges
    )

    print(data)


test_update_pair(
    _id="634588fd84e8922219888347",
    strategies=[{"remove": "super_trend"}],
    exchanges=[{"add": 'huobi'}, {"remove": "kraken"}],
)
