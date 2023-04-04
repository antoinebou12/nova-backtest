from novalabs.utils.backtest import BackTest
from datetime import datetime
from novalabs.utils.indicators import TechnicalIndicatorsCreation
from novalabs.utils.indicators import get_candlestick_name


def get_data(exchange: str, pair: str, candle: str):
    backtest = BackTest(
        exchange=exchange,
        strategy_name='lgbm',
        candle=candle,
        list_pairs=[pair],
        start=datetime(2018, 1, 1),
        end=datetime(2023, 1, 1),
        start_bk=1000,
        leverage=4,
        max_pos=4,
        max_holding=6
    )

    # import data
    df = backtest.get_historical_data(
        pair=pair
    )
    var_to_drop = ['ignore', 'next_open', 'globalLongShortRatio','topLongShortRatio',
        'topLongShortRatioPositions', 'buySellRatio', 'openInterestClose']
    return df.drop(var_to_drop, axis=1)

def test_get_candlestick_name():
    # Arrange
    expected_counts = {'Marubozu': 45, 'Doji': 30, 'Spinning Top': 25}

    # Act
    btc_1d = get_data(exchange='binance', pair='BTCUSDT', candle='1d')
    result = get_candlestick_name(btc_1d)

    # Assert
    assert result['candlestick_name'].value_counts().to_dict() == expected_counts