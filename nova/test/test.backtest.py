from nova.utils.backtest import BackTest
from datetime import datetime


def test_get_freq() -> None:
    test_candle = '15m'

    class_t = BackTest(
        candle=test_candle,
        list_pair="All pairs",
        start=datetime(2022, 5, 1),
        end=datetime(2022, 6, 1),
        fees=0.0004,
        max_pos=10,
        max_holding=15,
        geometric_sizes=False,
        start_bk=10000,
        slippage=False
    )

    assert class_t.get_freq() == '15min'

    test_candle = '30m'
    class_t.candle = test_candle
    assert class_t.get_freq() == '30min'

    test_candle = '1h'
    class_t.candle = test_candle




