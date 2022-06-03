from nova.api.nova_client import NovaClient
from decouple import config

nova_client = NovaClient(config('NovaAPISecret'))


bot_name = "bot_4"
position_type = "LONG"
value=1.0
state = "CLOSE"
entry_price=1000.0
exit_price= 1200
tp = 1200.0
sl = 900.0
exit_type = "TP"
profit = 200.0
fees = 2.0
token="BTC"
pair = "BTCUSDT"


def test_create_position():

    data = nova_client.create_position(
        bot_name=bot_name,
        post_type=position_type,
        value=value,
        state=state,
        entry_price=entry_price,
        take_profit=tp,
        stop_loss=sl,
        token=token,
        pair=pair
    )

    print(data)


# test_create_position()


def test_update_position():

    position_id = "629a3f7845dfda60b91b9cbb"

    data = nova_client.update_position(
        pos_id=position_id,
        pos_type=position_type,
        state="CLOSE",
        entry_price=entry_price,
        exit_price=exit_price,
        exit_type=exit_type,
        profit=profit,
        fees=fees,
        pair=pair
    )

    print(data)


# test_update_position()


def test_delete_position():
    id_to_delete = "629a3f7845dfda60b91b9cbb"

    data = nova_client.delete_position(
        position_id=id_to_delete
    )

    print(data)


# test_delete_position()


def test_read_position():
    id_to_read = "629a4f1345dfda60b91b9cc7"

    data = nova_client.read_position(
        position_id=id_to_read
    )

    print(data)


# test_read_position()


def test_read_positions():

    data = nova_client.read_positions()

    print(data)


# test_read_positions()

