from requests import Request, Session
import hmac
import base64
import json
import time
import hashlib
from novalabs.utils.helpers import interval_to_minutes, interval_to_milliseconds, milliseconds_to_interval
from novalabs.utils.constant import DATA_FORMATING
import pandas as pd
from datetime import datetime
import numpy as np

class Kucoin:

    def __init__(self,
                 key: str,
                 secret: str,
                 pass_phrase: str,
                 testnet: bool):
        self.api_key = key
        self.api_secret = secret
        self.pass_phrase = pass_phrase

        self.based_endpoint = "https://api-futures.kucoin.com"

        self._session = Session()

        self.historical_limit = 190

        self.pairs_info = self.get_pairs_info()

        self.leverage = 2

    def _send_request(self, end_point: str, request_type: str, params: dict = {}, signed: bool = False):

        to_use = "https://api-futures.kucoin.com" if not signed else self.based_endpoint
        request = Request(request_type, f'{to_use}{end_point}', data=json.dumps(params))
        prepared = request.prepare()

        timestamp = int(time.time() * 1000)

        prepared.headers['Content-Type'] = "application/json"
        prepared.headers['KC-API-KEY-VERSION '] = "2"
        prepared.headers['User-Agent'] = "NovaLabs"
        prepared.headers['KC-API-TIMESTAMP'] = str(timestamp)

        if signed:

            final_dict = ""
            if params:
                final_dict = json.dumps(params)

            sig_str = f"{timestamp}{request_type}{end_point}{final_dict}".encode('utf-8')
            signature = base64.b64encode(
                hmac.new(self.api_secret.encode('utf-8'), sig_str, hashlib.sha256).digest()
            )

            prepared.headers['KC-API-SIGN'] = signature
            prepared.headers['KC-API-KEY'] = self.api_key
            prepared.headers['KC-API-PASSPHRASE'] = self.pass_phrase

        response = self._session.send(prepared)

        return response.json()

    def get_server_time(self) -> int:
        """
        Returns:
            the timestamp in milliseconds
        """
        return self._send_request(
            end_point=f"/api/v1/timestamp",
            request_type="GET"
        )['data']

    def get_pairs_info(self):

        data = self._send_request(
            end_point=f"/api/v1/contracts/active",
            request_type="GET",
            signed=False
        )['data']

        pairs_info = {}

        for pair in data:

            if pair['status'] == "Open":

                if pair['multiplier'] > 0:
                    step_size = pair['lotSize'] * pair['multiplier']
                else:
                    step_size = pair['lotSize']

                pairs_info[pair['symbol']] = {}
                pairs_info[pair['symbol']]['quote_asset'] = pair['quoteCurrency']

                price_increment = np.format_float_positional(pair["tickSize"], trim='-')

                pairs_info[pair['symbol']]['maxQuantity'] = float(pair['maxOrderQty'])
                pairs_info[pair['symbol']]['minQuantity'] = float(step_size)

                pairs_info[pair['symbol']]['tick_size'] = float(pair['tickSize'])

                if float(pair['tickSize']) < 1:
                    pairs_info[pair['symbol']]['pricePrecision'] = int(str(price_increment)[::-1].find('.'))
                else:
                    pairs_info[pair['symbol']]['pricePrecision'] = 1

                pairs_info[pair['symbol']]['step_size'] = float(step_size)
                if step_size < 1:
                    pairs_info[pair['symbol']]['quantityPrecision'] = int(str(step_size)[::-1].find('.'))
                else:
                    pairs_info[pair['symbol']]['quantityPrecision'] = 1

                pairs_info[pair['symbol']]['multiplier'] = pair['multiplier']

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
        _interval_min = interval_to_minutes(interval)
        _interval_ms = interval_to_milliseconds(interval)

        _end_time = start_time + self.historical_limit * _interval_ms
        _endpoint = f"/api/v1/kline/query?symbol={pair}&granularity={_interval_min}&from={start_time}&to={_end_time}"
        return self._send_request(
            end_point=f'{_endpoint}',
            request_type="GET",
        )['data']

    def _get_earliest_timestamp(self, pair: str, interval: str):
        """
        Note the historical data for the
        of the time
        Args:
            pair: Name of symbol pair
            interval: interval in string
        return:
            the earliest valid open timestamp in milliseconds
        """

        current_time = (time.time() * 1000)
        _interval_ms = interval_to_milliseconds(interval)

        return int(current_time - 15 * _interval_ms * self.historical_limit)

    @staticmethod
    def _format_data(all_data: list, historical: bool = True) -> pd.DataFrame:
        """
        Args:
            all_data: output from _full_history

        Returns:
            standardized pandas dataframe
        """

        df = pd.DataFrame(all_data, columns=DATA_FORMATING['kucoin']['columns'])

        for var in DATA_FORMATING['kucoin']['num_var']:
            df[var] = pd.to_numeric(df[var], downcast="float")

        interval_ms = df['open_time'].iloc[1] - df['open_time'].iloc[0]

        clean_df = df

        if historical:

            final_data = df.drop_duplicates().dropna().reset_index(drop=True)

            _first_time = datetime.fromtimestamp(final_data.loc[0, 'open_time'] // 1000.0)
            _last_time = datetime.fromtimestamp(final_data.loc[len(final_data)-1, 'open_time'] // 1000.0)
            _freq = milliseconds_to_interval(interval_ms)

            final_timeseries = pd.DataFrame(
                pd.date_range(start=_first_time, end=_last_time, freq=_freq, tz='US/Eastern'),
                columns=['open_time']
            )

            final_timeseries['open_time'] = final_timeseries['open_time'].astype(np.int64) // 10 ** 6
            clean_df = final_timeseries.merge(final_data, on='open_time', how='left')

            all_missing = clean_df.isna().sum().sum()

            if all_missing > 0:
                print(f'Kucoin returned {all_missing} missing values ! Forward Fill Applied')
                clean_df = clean_df.ffill()

            clean_df['next_open'] = clean_df['open'].shift(-1)

        clean_df['close_time'] = clean_df['open_time'] + interval_ms - 1

        for var in ['open_time', 'close_time']:
            clean_df[var] = clean_df[var].astype(int)

        return clean_df.dropna()

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
                # exit the while loop
                break

            # increment next call by our timeframe
            start_time = temp_data[-1][0] + timeframe

            # exit loop if we reached end_ts before reaching klines
            if start_time >= end_ts:
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

