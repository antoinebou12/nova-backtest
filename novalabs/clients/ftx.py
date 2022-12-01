from requests import Request, Session
import time
import datetime
import hmac
from novalabs.utils.helpers import interval_to_milliseconds, milliseconds_to_interval
from novalabs.utils.constant import DATA_FORMATING
import pandas as pd
import numpy as np
import aiohttp
import asyncio
import json
import urllib.parse
from typing import Union
import math
from multiprocessing import Pool


class FTX:

    def __init__(self,
                 key: str,
                 secret: str,
                 testnet: bool = False
                 ):
        self.api_key = key
        self.api_secret = secret
        self.based_endpoint = "https://ftx.com/"
        self._session = Session()
        self.historical_limit = 1500
        self.pairs_info = self.get_pairs_info()
        self.holding_days = 5

    def _send_request(self, end_point: str, request_type: str, params: dict = None, signed: bool = False):
        if params is None:
            params = {}

        url = f'{self.based_endpoint}{end_point}'
        request = Request(request_type, url, data=json.dumps(params))
        prepared = request.prepare()
        prepared.headers['Content-Type'] = 'application/json'

        if signed:
            ts = int(time.time() * 1000)

            signature_payload = f'{ts}{request_type}{end_point}'

            if prepared.body:
                signature_payload += prepared.body

            signature_payload = signature_payload.encode()

            signature = hmac.new(self.api_secret.encode(), signature_payload, 'sha256').hexdigest()

            prepared.headers['FTX-KEY'] = self.api_key
            prepared.headers['FTX-SIGN'] = signature
            prepared.headers['FTX-TS'] = str(ts)

            prepared.headers['FTX-SUBACCOUNT'] = urllib.parse.quote('novalabs')

        response = self._session.send(prepared)
        data = response.json()

        if not data['success']:
            if data['error'] == 'Order not found' or data['error'] == 'Order already closed':
                return data
            else:
                print(data['error'])

        if 'result' in data.keys():
            return data['result']
        else:
            return data

    @staticmethod
    def get_server_time() -> int:
        """
        Note: FTX does not have any server time end point so we are simulating it with the time function
        Returns:
            the timestamp in milliseconds
        """
        return int(time.time() * 1000)

    def get_pairs_info(self) -> dict:
        data = self._send_request(
            end_point=f"/api/markets",
            request_type="GET"
        )

        pairs_info = {}

        for pair in data:

            if 'PERP' in pair['name']:

                _name = pair['name']

                pairs_info[_name] = {}
                pairs_info[_name]['quote_asset'] = 'USD'

                size_increment = np.format_float_positional(pair["sizeIncrement"], trim='-')
                price_increment = np.format_float_positional(pair["priceIncrement"], trim='-')

                pairs_info[_name]['maxQuantity'] = float(pair['largeOrderThreshold'])
                pairs_info[_name]['minQuantity'] = float(size_increment)

                pairs_info[_name]['tick_size'] = float(price_increment)
                if float(pair['priceIncrement']) < 1:
                    pairs_info[_name]['pricePrecision'] = int(str(price_increment)[::-1].find('.'))
                else:
                    pairs_info[_name]['pricePrecision'] = 1

                pairs_info[_name]['step_size'] = float(size_increment)
                if float(pair['sizeIncrement']) < 1:
                    pairs_info[_name]['quantityPrecision'] = int(str(size_increment)[::-1].find('.'))
                else:
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
        _start_time = int(start_time//1000)
        _end_time = int(end_time//1000)
        _interval = int(interval_to_milliseconds(interval)//1000)
        _endpoint = f"/api/markets/{pair}/candles?resolution={_interval}&start_time={_start_time}&end_time={_end_time}"
        return self._send_request(
            end_point=_endpoint,
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
        kline = self._get_candles(
            pair=pair,
            interval='4d',
            start_time=0,
            end_time=int(time.time()*1000)
        )
        return int(kline[0]['time'])

    def _format_data(self, all_data: list, historical: bool = True) -> pd.DataFrame:
        """
        Args:
            all_data: output from _combine_history
        Returns:
            standardized pandas dataframe
        """
        # Remove the last row if it's not finished yet
        df = pd.DataFrame(all_data)
        df.drop('startTime', axis=1, inplace=True)
        df.columns = ['open_time', 'open', 'high', 'low', 'close', 'volume']

        for var in DATA_FORMATING['ftx']['num_var']:
            df[var] = pd.to_numeric(df[var], downcast="float")

        interval_ms = df['open_time'].iloc[1] - df['open_time'].iloc[0]

        clean_df = df

        if historical:

            final_data = df.drop_duplicates().dropna().reset_index(drop=True)

            _first_time = datetime.datetime.fromtimestamp(final_data.loc[0, 'open_time'] // 1000.0)
            _last_time = datetime.datetime.fromtimestamp(final_data.loc[len(final_data)-1, 'open_time'] // 1000.0)
            _freq = milliseconds_to_interval(interval_ms)

            final_timeseries = pd.DataFrame(
                pd.date_range(start=_first_time, end=_last_time, freq=_freq, tz='US/Eastern'),
                columns=['open_time']
            )

            final_timeseries['open_time'] = final_timeseries['open_time'].astype(np.int64) // 10 ** 6
            clean_df = final_timeseries.merge(final_data, on='open_time', how='left')

            all_missing = clean_df.isna().sum().sum()

            if all_missing > 0:
                print(f'FTX returned {all_missing} missing values ! Forward Fill Applied')
                clean_df = clean_df.ffill()

            clean_df['next_open'] = clean_df['open'].shift(-1)

        clean_df['close_time'] = clean_df['open_time'] + interval_ms - 1

        for var in ['open_time', 'close_time']:
            clean_df[var] = clean_df[var].astype(int)

        return clean_df

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

            end_t = start_time + timeframe * self.historical_limit
            end_time = min(end_t, end_ts)

            # fetch the klines from start_ts up to max 500 entries or the end_ts if set
            temp_data = self._get_candles(
                pair=pair,
                interval=interval,
                start_time=start_time,
                end_time=end_time
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
            start_time = temp_data[-1]['time'] + timeframe

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
