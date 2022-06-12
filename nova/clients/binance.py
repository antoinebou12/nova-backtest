from binance.um_futures import UMFutures
from decouple import config
from datetime import datetime
from nova.clients.helpers import interval_to_milliseconds, convert_ts_str
import time


class Binance:

    def __init__(self,
                 key: str,
                 secret: str):

        self.client = UMFutures(key=key, secret=secret)
        self.historical_limit = 1000

    def _get_earliest_valid_timestamp(self, symbol: str, interval: str):
        """
        Get earliest valid open timestamp from Binance
        Args:
            symbol: Name of symbol pair e.g BNBBTC
            interval: Binance Kline interval

        :return: first valid timestamp
        """
        kline = self.client.klines(
            symbol=symbol,
            interval=interval,
            limit=1,
            startTime=0,
            endTime=int(time.time() * 1000)
        )
        return kline[0][0]

    def get_historical(self, pair: str, timeframe: str, start_time: str, end_time: str):
        """


        Args:
            pair:
            timeframe:
            start_time:
            end_time:

        Returns:

        """

        # init our list
        output_data = []

        # convert interval to useful value in seconds
        timeframe = interval_to_milliseconds(timeframe)

        # if a start time was passed convert it
        start_ts = convert_ts_str(start_time)

        # establish first available start timestamp
        if start_ts is not None:
            first_valid_ts = self._get_earliest_valid_timestamp(
                symbol=pair,
                interval=timeframe
            )
            start_ts = max(start_ts, first_valid_ts)

        # if an end time was passed convert it
        end_ts = convert_ts_str(end_time)
        if end_ts and start_ts and end_ts <= start_ts:
            return output_data

        idx = 0
        while True:
            # fetch the klines from start_ts up to max 500 entries or the end_ts if set
            temp_data = self.client.klines(
                symbol=pair,
                interval=timeframe,
                limit=self.historical_limit,
                startTime=start_ts,
                endTime=end_ts
            )

            # append this loops data to our output data
            if temp_data:
                output_data += temp_data

            # handle the case where exactly the limit amount of data was returned last loop
            # check if we received less than the required limit and exit the loop
            if not len(temp_data) or len(temp_data) < self.historical_limit:
                # exit the while loop
                break

            # increment next call by our timeframe
            start_ts = temp_data[-1][0] + timeframe

            # exit loop if we reached end_ts before reaching <limit> klines
            if end_ts and start_ts >= end_ts:
                break

            # sleep after every 3rd call to be kind to the API
            idx += 1
            if idx % 3 == 0:
                time.sleep(1)

        return self.client.klines(
            symbol=pair,
            interval=timeframe,
            startTime=start_time,
            endTime=end_time,
            limit=1000
        )


client = Binance(key=config("BinanceAPIKey"), secret=config("BinanceAPISecret"))

start = datetime(2020, 1, 1).strftime('%d %b, %Y')
end = datetime(2022, 1, 1).strftime('%d %b, %Y')


data = client.get_historical(
    pair='BTCUSDT',
    timeframe='1d',
    start_time=start,
    end_time=end
)


