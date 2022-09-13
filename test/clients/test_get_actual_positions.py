from nova.clients.clients import clients
from decouple import config


def asserts_get_actual_positions(
        exchange: str,
        info: dict
):

    client = clients(
        exchange=exchange,
        key=config(f"{exchange}TestAPIKey"),
        secret=config(f"{exchange}TestAPISecret"),
        testnet=True
    )

    # Check the current positions
    positions = client.get_actual_positions(
        list_pair=list(info.keys())
    )

    if len(positions) != 0:

        for _pair, _info in positions.items():

            client.exit_market_order(
                pair=_pair,
                side=_info['exit_side'],
                quantity=_info['position_size']
            )

    positions = client.get_actual_positions(
        list_pair=list(info.keys())
    )

    nb_pos = 0

    assert len(positions) == nb_pos

    for pair, value in info.items():

        print(f'Buy {pair} for {value["quantity"]} in position size')

        _side = 'BUY' if value["quantity"] > 0 else 'SELL'
        _type = 'LONG' if value["quantity"] > 0 else 'SHORT'

        client.enter_market_order(
            pair=pair,
            side=_side,
            quantity=abs(value["quantity"])
        )

        nb_pos += 1

        positions_ = client.get_actual_positions(list_pair=info.keys())

        assert len(positions_.keys()) == nb_pos
        assert positions_[pair]['position_size'] == abs(value["quantity"])
        assert positions_[pair]['type'] == _type

        assert isinstance(positions_[pair]['entry_price'], float)
        assert isinstance(positions_[pair]['unrealized_pnl'], float)

    new_positions = client.get_actual_positions(
        list_pair=list(info.keys())
    )

    print(new_positions)

    assert len(new_positions.keys()) == len(list(info.keys()))

    for pair, _info in new_positions.items():

        client.exit_market_order(
                pair=pair,
                side=_info['exit_side'],
                quantity=_info['position_size']
            )

    new_positions = client.get_actual_positions(
        list_pair=list(info.keys())
    )

    assert len(new_positions) == 0

    print(f"Test get_actual_positions for {exchange.upper()} successful")


def test_get_actual_positions():

    all_tests = [
        {
            'exchange': 'binance',
            'info': {
                'BTCUSDT': {'quantity': 0.01},
                'ETHUSDT': {'quantity': -0.1}
            }
        }
    ]

    for _test in all_tests:

        asserts_get_actual_positions(
            exchange=_test['exchange'],
            info=_test['info']

        )


test_get_actual_positions()
