from nova.api.client import NovaAPI
from decouple import config


def test_create_strategy(
        name,
        start_time,
        end_time,
        description,
        version,
        candles,
        leverage,
        max_position,
        trades,
        max_day_underwater,
        ratio_winning,
        ratio_sortino,
        ratio_sharp,
        max_down,
        monthly_fee,
        avg_profit,
        avg_hold_time,
        score,
):

    nova_client = NovaAPI(config('NovaAPISecret'))

    data = nova_client.create_strategy(
        name=name,
        start_time=start_time,
        end_time=end_time,
        description=description,
        version=version,
        candles=candles,
        leverage=leverage,
        max_position=max_position,
        trades=trades,
        max_day_underwater=max_day_underwater,
        ratio_winning=ratio_winning,
        ratio_sortino=ratio_sortino,
        ratio_sharp=ratio_sharp,
        max_down=max_down,
        monthly_fee=monthly_fee,
        avg_profit=avg_profit,
        avg_hold_time=avg_hold_time,
        score=score
    )

    print(data)

    assert data['createStrategy']['name'] == name


test_create_strategy(
    name='vmc',
    start_time=1577836800000,
    end_time=1640995200,
    description="This is my description for VMC",
    version='V1',
    candles='15m',
    leverage=2,
    max_position=6,
    trades=4000,
    max_day_underwater=96,
    ratio_winning=0.55,
    ratio_sortino=17.5,
    ratio_sharp=5.3,
    max_down=34.5,
    monthly_fee=200,
    avg_profit=1.02,
    avg_hold_time=11,
    score=8,
)

test_create_strategy(
    name='super_trend',
    start_time=1577836800000,
    end_time=1640995200,
    description="This is my description for Super Trend",
    version='V1',
    candles='1h',
    leverage=2,
    max_position=6,
    trades=3000,
    max_day_underwater=50,
    ratio_winning=0.60,
    ratio_sortino=18.3,
    ratio_sharp=7.4,
    max_down=25.9,
    monthly_fee=180,
    avg_profit=0.7,
    avg_hold_time=15,
    score=9,
)


def test_delete_strategy(strategy_id: str):

    nova_client = NovaAPI(config('NovaAPISecret'))
    data = nova_client.delete_strategy(
        params={
            "strategyId": strategy_id,
        }
    )
    print(data)
    assert data['deleteStrategy']


test_delete_strategy(strategy_id="63457af584e89222198882f0")


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

