from nova.api.nova_client import NovaClient
from decouple import config
import json

nova_client = NovaClient(config('NovaAPISecret'))

with open('database/analysis/test_json.json', 'r') as f:
  data = json.load(f)


const_name = 'ichimokuV1'
start_time = 1577836800
end_time = 1640995200
version = 'V1'
candles = '15m'
leverage = 4
max_position = 15
trades = 8000
max_day_underwater = 96
ratio_winning = 0.47
ratio_sortino = 18.39
ratio_sharp = 5.18
max_down = 34.5
monthly_fee = 150.6
avg_profit = 1.02
avg_hold_time = 12.5
score = 8


def test_create_strategy():

    data = nova_client.create_strategy(
        name='ichimokuV1',
        start_time=1577836800,
        end_time=1640995200,
        version='V1',
        candles='15m',
        leverage=4,
        max_position=15,
        trades=8000,
        max_day_underwater=96,
        ratio_winning=0.47,
        ratio_sortino=18.39,
        ratio_sharp=5.18,
        max_down=34.5,
        monthly_fee=150.6,
        avg_profit=1.02,
        avg_hold_time=12.5,
        score=8
    )

    assert data['createStrategy']['name'] == 'ichimokuV1'

def test_read_strategy():
    name_test = "random"

    data = nova_client.read_strategy(strat_name=name_test)

    print(data)


def test_read_strategies():

    data = nova_client.read_strategies()

    print(data)

def test_update_strategy():

    id_to_update = "62923c588a810ee6a20fefa3"

    to_update = {
        "input": {
            "id": id_to_update,
            "name": "ichimokuV2"

        }
    }

    data = nova_client.update_strategy(params=to_update)

    print(data)


def test_delete_strategy():

    id_to_delete = "6298de4b8a810ee6a20fefb0"

    to_delete = {
        "strategyId": id_to_delete,
    }

    data = nova_client.delete_strategy(params=to_delete)

    print(data)


test_delete_strategy()