from requests import Request, Session
import hmac
import base64
import time
import hashlib
from novalabs.utils.helpers import interval_to_milliseconds
from datetime import datetime, date
import pandas as pd
from novalabs.utils.constant import DATA_FORMATING
import json


class Coinbase:

    def __init__(self,
                 key: str,
                 secret: str,
                 pass_phrase: str,
                 testnet: bool):
        self.api_key = key
        self.api_secret = secret
        self.pass_phrase = pass_phrase

        self.based_endpoint = "https://api.pro.coinbase.com"
        if testnet:
            self.based_endpoint = "https://api-public.sandbox.exchange.coinbase.com"

        self._session = Session()

        self.pairs_info = self.get_pairs_info()

        self.max_historical = 10000
        self.historical_limit = 290

    def _send_request(self, end_point: str, request_type: str, params: dict = {}, signed: bool = False):

        timestamp = str(int(time.time()))

        to_use = "https://api.pro.coinbase.com" if not signed else self.based_endpoint
        request = Request(request_type, f'{to_use}{end_point}', data=json.dumps(params))
        prepared = request.prepare()

        prepared.headers['Content-Type'] = "application/json"

        if signed:
            _params = ""
            if params is not None:
                _params = prepared.body

            message = ''.join([timestamp, request_type, end_point, _params])
            message = message.encode('ascii')
            hmac_key = base64.b64decode(self.api_secret)
            signature = hmac.new(hmac_key, message, hashlib.sha256)
            signature_b64 = base64.b64encode(signature.digest()).decode('utf-8')

            prepared.headers['CB-ACCESS-KEY'] = self.api_key
            prepared.headers['CB-ACCESS-SIGN'] = signature_b64
            prepared.headers['CB-ACCESS-PASSPHRASE'] = self.pass_phrase
            prepared.headers['CB-ACCESS-TIMESTAMP'] = timestamp

        response = self._session.send(prepared)

        return response.json()

    @staticmethod
    def get_server_time() -> int:
        """
        Returns:
            the timestamp in milliseconds
        """
        return int(time.time() * 1000)

    def get_pairs_info(self) -> dict:
        """
        Returns:
            the timestamp in milliseconds
        """
        data = self._send_request(
            end_point=f"/products",
            request_type="GET"
        )

        pairs_info = {}

        for pair in data:

            if not pair['trading_disabled'] and pair['quote_currency'] in ['USD', 'USDT', 'USDC']:
                pairs_info[pair['id']] = {}
                pairs_info[pair['id']]['quote_asset'] = pair['quote_currency']
                pairs_info[pair['id']]['maxQuantity'] = float('inf')
                pairs_info[pair['id']]['minQuantity'] = 0.0
                pairs_info[pair['id']]['tick_size'] = float(pair['base_increment'])
                pairs_info[pair['id']]['pricePrecision'] = int(str(pair['base_increment'])[::-1].find('.'))
                pairs_info[pair['id']]['quantityPrecision'] = 6

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

        _start_time = datetime.fromtimestamp(int(start_time // 1000)).isoformat()
        _interval_ms = interval_to_milliseconds(interval)
        _interval = str(int(_interval_ms//1000))
        end_time = start_time + _interval_ms * self.historical_limit
        _end_time = datetime.fromtimestamp(int(end_time // 1000)).isoformat()

        data = self._send_request(
            end_point=f'/products/{pair}/candles?start={_start_time}&end={_end_time}&granularity={_interval}',
            request_type="GET",
            params={
                'start': _start_time,
                'granularity': _interval,
                'end': _end_time
            }
        )

        return data

    def _get_earliest_timestamp(self, pair: str, interval: str):
        """
        Args:
            pair: Name of symbol pair
            interval: interval in string
        return:
            the earliest valid open timestamp in milliseconds
        """

        earliest = int(datetime(2022, 1, 1).timestamp() * 1000)
        today = int(time.time() * 1000)

        maximum_historical = today - self.max_historical * interval_to_milliseconds(interval)

        return max([earliest, maximum_historical])

    @staticmethod
    def _format_data(all_data: list, historical: bool = True) -> pd.DataFrame:
        """
        Args:
            all_data: output from _full_history

        Returns:
            standardized pandas dataframe
        """

        df = pd.DataFrame(all_data, columns=DATA_FORMATING['coinbase']['columns'])
        df = df.sort_values(by='open_time').reset_index(drop=True)
        df['open_time'] = df['open_time'] * 1000
        interval_ms = df['open_time'].iloc[1] - df['open_time'].iloc[0]
        df['close_time'] = df['open_time'] + interval_ms - 1

        for var in DATA_FORMATING['coinbase']['num_var']:
            df[var] = pd.to_numeric(df[var], downcast="float")

        for var in DATA_FORMATING['coinbase']['date_var']:
            df[var] = pd.to_numeric(df[var], downcast="integer")

        if historical:
            df['next_open'] = df['open'].shift(-1)

        return df.dropna().drop_duplicates('open_time')

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

            # fetch the klines from start_ts up to max 500 entries or the end_ts if set
            temp_data = self._get_candles(
                pair=pair,
                interval=interval,
                start_time=start_time,
                end_time=end_ts
            )

            # append this loops data to our output data
            if temp_data:
                klines += temp_data

            # handle the case where exactly the limit amount of data was returned last loop
            # check if we received less than the required limit and exit the loop
            if not len(temp_data) or len(temp_data) < self.historical_limit:
                print('exit_1')
                # exit the while loop
                break

            # increment next call by our timeframe
            start_time = temp_data[0][0] * 1000 + timeframe

            print(f'Request # {idx}')
            print(start_time, end_ts)

            # exit loop if we reached end_ts before reaching <limit> klines
            if start_time >= end_ts:
                print('exit_2')
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
