from nova.utils.helpers import get_timedelta_unit
from datetime import timedelta

def asserts_get_timedelta_unit(interval, result):
    data = get_timedelta_unit(interval)
    assert result == data
    print('Test get_timedelta_unit passed')


def test_get_timedelta_unit():
    all_tests = [
        {
            'interval': '15m',
            'result': timedelta(minutes=15)
        },
        {
            'interval': '1h',
            'result': timedelta(hours=1)
        },
        {
            'interval': '2h',
            'result': timedelta(hours=2)
        },
    ]

    for test in all_tests:
        asserts_get_timedelta_unit(
            interval=test['interval'],
            result=test['result']
        )


test_get_timedelta_unit()
