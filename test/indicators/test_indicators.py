from novalabs.utils.backtest import BackTest
from datetime import datetime
from novalabs.utils.indicators import TechnicalIndicatorsCreation


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

# Get data
btc_1h = get_data(exchange='binance', pair='BTCUSDT', candle='1h')
btc_1d = get_data(exchange='binance', pair='BTCUSDT', candle='1d')


from novalabs.utils.indicators import get_candlestick_name
new = get_candlestick_name(btc_1d)
new['candlestick_name'].value_counts()


