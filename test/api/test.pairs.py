from nova.api.client import NovaClient
from decouple import config


nova_client = NovaClient(config('NovaAPISecret'))


value = "TEST"
name = "TEST"
fiat = "USDT"
available_st = [{"name": "ichimokuV1"}]
available_ex = ['binance', 'ftx']


def test_create_pair():

    data = nova_client.create_pair(
        value=value,
        name=name,
        fiat=fiat,
        strategies=available_st,
        exchanges=available_ex
    )

    assert data['createPair']['name'] == 'TEST'

# test_create_pair()


def test_delete_pair():

    id_to_delete = "6298deeb8a810ee6a20fefbb"

    data = nova_client.delete_pair(
        pair_id=id_to_delete
    )

    print(data)

# test_delete_pair()


def test_update_pair():

    id_to_update = "629902b245dfda60b91b9c77"
    original_value = "TEST"
    original_name = "TEST"
    original_fiat = "USDT"

    to_update = {
        "input": {
            "id": id_to_update,
            "value": original_value,
            "name": original_name,
            "fiat": original_fiat,
            "available_exchange": ['kraken'],
            "available_strategy": [{"name": "random"}]

        }
    }

    data = nova_client.update_pair(
        params=to_update
    )

    print(data)

# test_update_pair()


def test_read_pair():

    id_to_claim = "629902b245dfda60b91b9c77"

    data = nova_client.read_pair(pair_id=id_to_claim)

    print(data)

# test_read_pair()


def test_read_pairs():

    data = nova_client.read_pairs()

    print(data)

# test_read_pairs()

