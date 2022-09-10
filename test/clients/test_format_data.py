import pandas as pd

from nova.clients.clients import clients
from decouple import config
from nova.utils.constant import STD_CANDLE_FORMAT


def test_format_data(exchange: str, pair: str, interval: str, start_time: int, end_time: int):

    client = clients(
        exchange=exchange,
        key=config(f"{exchange}TestAPIKey"),
        secret=config(f"{exchange}TestAPISecret"),
    )

    data = client._get_candles(
        pair=pair,
        interval=interval,
        start_time=start_time,
        end_time=end_time
    )

    hist_data = client._format_data(
        all_data=data,
        historical=True
    )

    data = client._format_data(
        all_data=data,
        historical=False
    )

    assert type(hist_data) == pd.DataFrame
    assert type(data) == pd.DataFrame

    assert 'next_open' in list(hist_data.columns)
    assert 'next_open' not in list(data.columns)

    for var in STD_CANDLE_FORMAT:
        assert var in list(hist_data.columns)
        assert var in list(data.columns)

        assert hist_data.dtypes[var] == 'int64' or hist_data.dtypes[var] == 'float32'
        assert data.dtypes[var] == 'int64' or data.dtypes[var] == 'float32'

    assert 'next_open' not in list(data.columns)

    for df in [data, hist_data]:
        assert len(str(df.loc[0, 'open_time'])) == 13
        assert len(str(df.loc[0, 'close_time'])) == 13
        assert str(df.loc[0, 'open_time'])[-3:] == '000'
        assert str(df.loc[0, 'close_time'])[-3:] == '999'

    assert 'open_time_datetime' in list(data.columns)
    assert str(data.dtypes['open_time_datetime']) == 'datetime64[ns]'

    print(f"Test _get_historical_data for {exchange.upper()} successful")


test_format_data('binance', 'BTCUSDT', '1d', 1631210861000, 1662746861000)
