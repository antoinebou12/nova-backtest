from nova.utils.helpers import convert_max_holding_to_candle_nb


def asserts_convert_max_holding_to_candle_nb(interval, holding_hour, result):
    data = convert_max_holding_to_candle_nb(interval, holding_hour)
    assert result == data
    print('Test convert_max_holding_to_candle_nb passed')


def test_convert_max_holding_to_candle_nb():
    all_tests = [
        {
            'interval': '15m',
            'holding_hour': 12,
            'result': 48
        },
        {
            'interval': '1h',
            'holding_hour': 12,
            'result': 12
        },
        {
            'interval': '2h',
            'holding_hour': 12,
            'result': 6
        },
    ]

    for test in all_tests:
        asserts_convert_max_holding_to_candle_nb(
            interval=test['interval'],
            holding_hour=test['holding_hour'],
            result=test['result']
        )


test_convert_max_holding_to_candle_nb()
