from requests import Request, Session
import json
from novalabs.utils.helpers import interval_to_oanda_granularity, interval_to_milliseconds
import pandas as pd
from datetime import datetime
import time

class Oanda:

    def __init__(self,
                 key: str = "",
                 secret: str = "",
                 testnet: bool = False
                 ):

        self.api_key = key
        self.api_secret = secret
        self.based_endpoint = "	https://api-fxpractice.oanda.com" if testnet else "https://api-fxtrade.oanda.com"
        self._session = Session()
        self.historical_limit = 4500

        self.pairs_info = self.get_pairs_info()

    def _send_request(self, end_point: str, request_type: str, params: dict = None, signed: bool = False):
        url = f'{self.based_endpoint}{end_point}'
        request = Request(request_type, url, data=json.dumps(params))
        prepared = request.prepare()
        prepared.headers['Content-Type'] = 'application/json'
        prepared.headers['OANDA-Agent'] = 'NovaLabs'
        prepared.headers['Authorization'] = f'Bearer {self.api_secret}'
        prepared.headers['Accept-Datetime-Format'] = 'UNIX'

        response = self._session.send(prepared)
        return response.json()

    @staticmethod
    def get_server_time() -> int:
        """
        Note: FTX does not have any server time end point so we are simulating it with the time function
        Returns:
            the timestamp in milliseconds
        """
        return int(time.time() * 1000)

    def get_pairs_info(self):
        response = self._send_request(
            end_point=f"/v3/accounts/{self.api_key}/instruments",
            params={"accountID": self.api_key},
            request_type="GET"
        )['instruments']

        pairs_info = {}

        for pair in response:

            if pair['type'] == 'CURRENCY':

                _name = pair['name']

                pairs_info[_name] = {}

                pairs_info[_name]['maxQuantity'] = float(pair['maximumOrderUnits'])
                pairs_info[_name]['minQuantity'] = float(pair['minimumTradeSize'])

                pairs_info[_name]['pricePrecision'] = int(pair['displayPrecision'])
                pairs_info[_name]['quantityPrecision'] = 1

        return pairs_info

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

        gran = interval_to_oanda_granularity(interval=interval)

        _start = start_time/1000
        _end = end_time/1000
        _args = f"?price=M&granularity={gran}&from={_start}&to={_end}"

        return self._send_request(
            end_point=f"/v3/instruments/{pair}/candles{_args}",
            params={
                "price": "M",
                "granularity": gran,
                "from": str(_start),
                "to": str(_end)
            },
            request_type="GET"
        )

    def _get_earliest_timestamp(self, pair: str, interval: str):
        """
        Note we are using an interval of 4 days to make sure we start at the beginning
        of the time
        Args:
            pair: Name of symbol pair
            interval: interval in string
        return:
            the earliest valid open timestamp in milliseconds
        """

        start_year = 2018
        starting_date = int(datetime(start_year, 1, 1).timestamp())
        gran = interval_to_oanda_granularity(interval=interval)

        _args = f"?price=M&granularity={gran}&from={starting_date}&count=10"

        response = self._send_request(
            end_point=f"/v3/instruments/{pair}/candles{_args}",
            params={
                "price": "M",
                "granularity": gran,
                "count": 10,
                "from": str(starting_date),
            },
            request_type="GET"
        )['candles'][0]['time']

        return int(float(response) * 1000)

    def _format_data(self, all_data: list, historical: bool = True) -> pd.DataFrame:
        """
        Args:
            all_data: output from _combine_history
        Returns:
            standardized pandas dataframe
        """

        final = {
            'open_time': [],
            'open': [],
            'high': [],
            'low': [],
            'close': [],
            'volume': [],
        }

        for info in all_data:
            final['open_time'].append(int(float(info['time']) * 1000))
            final['open'].append(float(info['mid']['o']))
            final['high'].append(float(info['mid']['h']))
            final['low'].append(float(info['mid']['l']))
            final['close'].append(float(info['mid']['c']))
            final['volume'].append(float(info['volume']))

        df = pd.DataFrame(final)

        interval_ms = df['open_time'].iloc[1] - df['open_time'].iloc[0]

        df['close_time'] = df['open_time'] + interval_ms - 1

        for var in ['open_time', 'close_time']:
            df[var] = df[var].astype(int)

        if historical:
            df['next_open'] = df['open'].shift(-1)

        return df.dropna().drop_duplicates()

    def get_historical_data(self, pair: str, interval: str, start_ts: int, end_ts: int) -> pd.DataFrame:
        """
        Note : There is a problem when computing the earliest timestamp for pagination, it seems that the
        earliest timestamp computed in "days" does not match the minimum timestamp in hours.

        In the
        Args:
            pair: pair to get information from
            interval: granularity of the candle ['1m', '1h', ... '1d']
            start_ts: timestamp in milliseconds of the starting date
            end_ts: timestamp in milliseconds of the end date
        Returns:
            historical data requested in a standardized pandas dataframe
        """
        # init our list
        klines = []

        # convert interval to useful value in seconds
        timeframe = interval_to_milliseconds(interval)

        first_valid_ts = self._get_earliest_timestamp(
            pair=pair,
            interval=interval
        )

        start_time = max(start_ts, first_valid_ts)

        idx = 0
        while True:

            print(f'Request # {idx}')

            end_t = start_time + timeframe * self.historical_limit
            end_time = min(end_t, end_ts)

            # fetch the klines from start_ts up to max 500 entries or the end_ts if set
            temp_data = self._get_candles(
                pair=pair,
                interval=interval,
                start_time=start_time,
                end_time=end_time
            )['candles']

            # append this loops data to our output data
            if temp_data:
                klines += temp_data

            if len(temp_data) == 0:
                break
            # handle the case where exactly the limit amount of data was returned last loop
            # check if we received less than the required limit and exit the loop

            # increment next call by our timeframe
            start_time = float(temp_data[-1]['time']) * 1000 + timeframe

            # exit loop if we reached end_ts before reaching <limit> klines
            if end_time and start_time >= end_ts:
                break

            # sleep after every 3rd call to be kind to the API
            idx += 1
            if idx % 3 == 0:
                time.sleep(1)

        data = self._format_data(all_data=klines)

        return data[(data['open_time'] >= start_ts) & (data['open_time'] <= end_ts)]

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
        df = self.get_historical_data(
            pair=pair,
            interval=interval,
            start_ts=end_date_data_ts,
            end_ts=int(time.time() * 1000)
        )
        return pd.concat([current_df, df], ignore_index=True).drop_duplicates(subset=['open_time'])
