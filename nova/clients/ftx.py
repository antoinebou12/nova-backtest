from requests import Request, Session
import time
import hmac
from nova.utils.helpers import interval_to_milliseconds
from nova.utils.constant import DATA_FORMATING, STD_CANDLE_FORMAT
import pandas as pd


class FTX:

    def __init__(self,
                 key: str,
                 secret: str):
        self.api_key = key
        self.api_secret = secret
        self.based_endpoint = "https://ftx.com/api"
        self._session = Session()
        self.historical_limit = 1500

    # API REQUEST FORMAT
    def _send_request(self, end_point: str, request_type: str, params: dict = None, signed: bool = False):
        if params is None:
            params = {}

        url = f'{self.based_endpoint}{end_point}'
        request = Request(request_type, url, params=params)
        prepared = request.prepare()

        if signed:
            ts = int(time.time() * 1000)
            signature_payload = f'{ts}{request_type}{url}'.encode()
            signature = hmac.new(self.api_secret.encode(), signature_payload, 'sha256').hexdigest()
            signature_payload += prepared.body
            prepared.headers['FTX-KEY'] = self.api_key
            prepared.headers['FTX-SIGN'] = signature
            prepared.headers['FTX-TS'] = str(ts)

        response = self._session.send(prepared)
        return response.json()

    # STANDARDIZED BACKTEST
    @staticmethod
    def get_server_time() -> int:
        """
        Returns:
            the timestamp in milliseconds
        """
        return int(time.time() * 1000)

    def get_all_pairs(self):
        """
        Notes:
            Only Perpetual contract
        Returns:
            list of all the pairs that we can trade on.
        """
        data = self._send_request(
            end_point=f"/futures",
            request_type="GET"
        )
        list_pairs = []
        for x in data['result']:
            if x['perpetual']:
                list_pairs.append(x['name'])
        return list_pairs

    def _get_candles(self, pair: str, interval: str, start_time: int, end_time: int):
        """
        Args:
            pair: pair to get information from
            interval: granularity of the candle ['1m', '1h', ... '1d']
            start_time: timestamp in milliseconds of the starting date
            end_time: timestamp in milliseconds of the end date
        Returns:
            the none formatted candle information requested
        """
        _start_time = int(start_time/1000)
        _end_time = int(end_time/1000)
        _interval = int(interval_to_milliseconds(interval) / 1000)
        _endpoint = f"/markets/{pair}/candles?resolution={_interval}&start_time={_start_time}&end_time={_end_time}"
        data = self._send_request(
            end_point=_endpoint,
            request_type="GET"
        )
        return data['result']

    def _get_earliest_valid_timestamp(self, pair: str):
        """
        Args:
            pair: Name of symbol pair
        return:
            the earliest valid open timestamp in milliseconds
        """
        kline = self._get_candles(
            pair=pair,
            interval='2d',
            start_time=0,
            end_time=int(time.time()*1000)
        )
        return int(kline[0]['time'])

    def _combine_history(self, pair: str, interval: str, start_time: int, end_time: int):
        """
        Args:
            pair: pair to get information from
            interval: granularity of the candle ['1m', '1h', ... '1d']
            start_time: timestamp in milliseconds of the starting date
            end_time: timestamp in milliseconds of the end date
        Returns:
            the complete raw data history desired -> multiple requested could be executed
        """

        # init our list
        output_data = []

        # convert interval to useful value in seconds
        timeframe = interval_to_milliseconds(interval)

        first_valid_ts = self._get_earliest_valid_timestamp(
            pair=pair,
        )
        start_ts = max(start_time, first_valid_ts)

        idx = 0
        while True:

            end_t = start_ts + timeframe * self.historical_limit
            end_ts = min(end_t, end_time)

            # fetch the klines from start_ts up to max 500 entries or the end_ts if set
            temp_data = self._get_candles(
                pair=pair,
                interval=interval,
                start_time=start_ts,
                end_time=end_ts
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
            start_ts = temp_data[-1]['time'] + timeframe

            # exit loop if we reached end_ts before reaching <limit> klines
            if end_ts and start_ts >= end_time:
                break

            # sleep after every 3rd call to be kind to the API
            idx += 1
            if idx % 3 == 0:
                time.sleep(1)

        return output_data

    def _format_data(self, all_data: list, interval: str) -> pd.DataFrame:
        """
        Args:
            all_data: output from _combine_history
        Returns:
            standardized pandas dataframe
        """
        # Remove the last row if it's not finished yet
        if self.get_server_time() < all_data[-1]['time']:
            del all_data[-1]
        df = pd.DataFrame(all_data)
        df.drop('startTime', axis=1, inplace=True)
        df.columns = ['open_time', 'open', 'high', 'low', 'close', 'volume']

        timeframe = interval_to_milliseconds(interval)

        for var in DATA_FORMATING['ftx']['num_var']:
            df[var] = pd.to_numeric(df[var], downcast="float")

        df['close_time'] = df['open_time'] + timeframe - 1
        df['next_open'] = df['open'].shift(-1)
        return df[STD_CANDLE_FORMAT].dropna()

    def get_historical(self, pair: str, interval: str, start_time: int, end_time: int) -> pd.DataFrame:
        """
        Args:
            pair: pair to get information from
            interval: granularity of the candle ['1m', '1h', ... '1d']
            start_time: timestamp in milliseconds of the starting date
            end_time: timestamp in milliseconds of the end date
        Returns:
            historical data requested in a standardized pandas dataframe
        """
        data = self._combine_history(
            pair=pair,
            interval=interval,
            start_time=start_time,
            end_time=end_time
        )

        return self._format_data(all_data=data, interval=interval)

    def update_historical(self, pair: str, interval: str, current_df: pd.DataFrame) -> pd.DataFrame:
        """
        Note:
            It will automatically download the latest data  points (excluding the candle not yet finished)
        Args:
            pair: pair to get information from
            interval: granularity of the candle ['1m', '1h', ... '1d']
            current_df: pandas dataframe of the current data
        Returns:
            a concatenated dataframe of the current data and the new data
        """

        end_date_data_ts = current_df['open_time'].max()
        data = self._combine_history(
            pair=pair,
            interval=interval,
            start_time=end_date_data_ts,
            end_time=int(time.time() * 1000)
        )
        format_df = self._format_data(all_data=data, interval=interval)
        return pd.concat([current_df, format_df], ignore_index=True).drop_duplicates()






