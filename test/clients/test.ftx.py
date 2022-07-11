from nova.clients.ftx import FTX
from decouple import config
from datetime import datetime
from nova.utils.helpers import convert_ts_str


client = FTX(key=config("ftxAPIKey"), secret=config("ftxAPISecret"))

start_timing = datetime(2022, 1, 1).strftime('%d %b, %Y')
end_timing = datetime(2022, 4, 1).strftime('%d %b, %Y')

start_ts = convert_ts_str(start_timing)
end_ts = convert_ts_str(end_timing)
#
# data = client._get_candles(
#     pair="BTC-PERP",
#     interval="15m",
#     start_time=start_ts,
#     end_time=end_ts
# )

# earliest = client._get_earliest_valid_timestamp(
#     pair="BTC-PERP",
# )

data = client.get_historical(
    pair="BTC-PERP",
    interval="15m",
    start_time=start_ts,
    end_time=end_ts
)

data_updated = client.update_historical(
    pair="BTC-PERP",
    interval="15m",
    current_df=data
)



