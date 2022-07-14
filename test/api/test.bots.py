from nova.api.client import NovaClient
from decouple import config


nova_client = NovaClient(config('NovaAPISecret'))


exchange= "binance"
maxDown= 0.2
bankRoll= 1000
totalProfit = 0
status = "offline"
strategy = {
    "name": "random"
}
exchangeKey = {
    "id": "628ebd07f829abdddfcf467c",
    "name": "MaelitoTest"
}
pairs = [{"pair": "TESTUSDT"}]


def test_create_bot():

    _params = {
        "input": {
            "exchange": exchange,
            "maxDown": maxDown,
            "bankRoll": bankRoll,
            "totalProfit": totalProfit,
            "status": status,
            "bot": strategy,
            "exchangeKey": exchangeKey,
            "pairs": pairs,
        }
    }

    data = nova_client.create_bot(
        params=_params
    )

    print(data)


def test_update_bot():
    _params = {
        "input": {
            "id": "629a092345dfda60b91b9ca1",
            "name": "bot_5",
            "exchange": exchange,
            "maxDown": 0.3,
            "bankRoll": 2000,
            "totalProfit": totalProfit,
            "status": status,
            "bot": strategy,
        }
    }

    data = nova_client.update_bot(
        params=_params
    )

    print(data)


def test_delete_bot():

    id_to_delete = "629a092345dfda60b91b9ca1"

    data = nova_client.delete_bot(
        id_bot=id_to_delete
    )

    print(data)


def test_read_bot():
    to_read = "628fc2843f4f0349b93120a7"

    data = nova_client.read_bot(
        _bot_id=to_read
    )

    print(data)

test_read_bot()


def test_read_bot():
    data = nova_client.read_bots()
    print(data)


test_read_bot()