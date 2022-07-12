from nova.clients.clients import clients
from decouple import config
import time


def test_get_actual_positions(
        exchange: str,
        list_pair: list
):

    client = clients(
        exchange=exchange,
        key=config(f"{exchange}APIKey"),
        secret=config(f"{exchange}APISecret"),
    )

    # Check the current positions
    positions = client.get_actual_positions(list_pair=list_pair)

    if len(positions) == 0:

        print(f'Buy {list_pair[0]} for 0.001 quantity')

        order_response = client.open_close_order(
            pair=list_pair[0],
            side='BUY',
            quantity=0.001
        )

        positions_two = client.get_actual_positions(list_pair=list_pair)

        assert positions_two[list_pair[0]]['position_amount'] == order_response['origQty']
        assert positions_two[list_pair[0]]['position_amount'] == '0.001'

        client.open_close_order(
            pair=list_pair[0],
            side='SELL',
            quantity=0.001
        )

        positions_three = client.get_actual_positions(list_pair=list_pair)
        assert len(positions_three) == 0


_list_pair = ['BTCUSDT', 'ETHUSDT']
test_get_actual_positions(exchange='binance', list_pair=_list_pair)

