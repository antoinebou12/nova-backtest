from nova.clients.binance import Binance
from decouple import config
from datetime import datetime
from nova.clients.helpers import convert_ts_str


client = Binance(key=config("BinanceAPIKey"), secret=config("BinanceAPISecret"))

# data = client.get_position_info()
#
# data = client.get_balance()

# client.change_leverage(
#     pair="BTCUSDT",
#     leverage=4,
# )

# start_timing = datetime(2022, 1, 1).strftime('%d %b, %Y')
# end_timing = datetime(2022, 4, 1).strftime('%d %b, %Y')
#
# start_ts = convert_ts_str(start_timing)
# end_ts = convert_ts_str(end_timing)
#
# data = client.get_candles(
#     pair="BTCUSDT",
#     interval="1d",
#     start_time=start_ts,
#     end_time=end_ts
# )

# data = client.get_tickers_price("BTCUSDT")

data = client.open_position_order(
    pair="BTCUSDT",
    side="BUY",
    quantity=0.0012
)






