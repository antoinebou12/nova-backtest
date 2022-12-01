import time
from novalabs.utils.helpers import interval_to_milliseconds
from novalabs.utils.constant import DATA_FORMATING
import pandas as pd
from requests import Request, Session
import hmac
import hashlib
import base64
import numpy as np
from typing import Union
import aiohttp
import asyncio
import datetime


class Kraken:

    def __init__(
            self,
            key: str,
            secret: str,
            testnet: bool = False
    ):

        self.api_key = key
        self.api_secret = secret
        self.based_endpoint = "https://futures.kraken.com/derivatives"

        if testnet:
            self.based_endpoint = "https://demo-futures.kraken.com/derivatives"

        self._session = Session()

        self.historical_limit = 4990

        self.pairs_info = self.get_pairs_info()

    def _send_request(self, end_point: str,
                      request_type: str,
                      signed: bool = False,
                      params: str = "",
                      is_ohlc: bool = False):

        to_use = "https://futures.kraken.com/derivatives" if not signed else self.based_endpoint

        if is_ohlc:
            to_use = 'https://futures.kraken.com'

        final_end_point = end_point

        if params != "":
            final_end_point += '?' + params

        request = Request(request_type, f'{to_use}{final_end_point}')
        prepared = request.prepare()
        prepared.headers['Content-Type'] = "application/json;charset=utf-8"
        prepared.headers['User-Agent'] = "NovaLabs"

        if signed:
            prepared.headers['apiKey'] = self.api_key
            nonce = str(int(time.time() * 1000))
            concat_str = (params + nonce + end_point).encode()
            sha256_hash = hashlib.sha256(concat_str).digest()

            signature = hmac.new(base64.b64decode(self.api_secret),
                                 sha256_hash,
                                 hashlib.sha512
                                 )

            rebase = base64.b64encode(signature.digest())

            prepared.headers['nonce'] = nonce
            prepared.headers['authent'] = rebase.decode()

        response = self._session.send(prepared)

        return response.json()

    @staticmethod
    def get_server_time() -> int:
        """
        Returns:
            the timestamp in milliseconds
        """
        return int(time.time() * 1000)

    def get_pairs_info(self):
        data = self._send_request(
            end_point=f"/api/v3/instruments",
            request_type="GET",
        )['instruments']

        output = {}

        for pair in data:

            if pair['type'] == 'flexible_futures' and pair['tradeable']:

                decimal_notation = np.format_float_positional(pair['tickSize'], trim="-")
                decimal = decimal_notation[::-1].find('.')

                precision = pair['tickSize'] if pair['tickSize'] >= 1 else decimal

                output[pair['symbol']] = {}
                output[pair['symbol']]['quote_asset'] = "USD"
                output[pair['symbol']]['tick_size'] = float(pair['tickSize'])
                output[pair['symbol']]['pricePrecision'] = precision
                output[pair['symbol']]['maxQuantity'] = pair['maxPositionSize']
                output[pair['symbol']]['minQuantity'] = 1 / (10 ** pair['contractValueTradePrecision'])
                output[pair['symbol']]['quantityPrecision'] = pair['contractValueTradePrecision']

        return output

    def _get_candles(self, pair: str, interval: str, start_time: int, end_time: int, limit: int = None):
        """
        Args:
            pair: pair to get information from
            interval: granularity of the candle ['1m', '1h', ... '1d']
            start_time: timestamp in milliseconds of the starting date
            end_time: timestamp in milliseconds of the end date
            limit: number of data points returned by binance

        Returns:
            the none formatted candle information requested
        """

        _start_time = start_time // 1000
        _end_time = end_time // 1000

        return self._send_request(
            end_point=f"/api/charts/v1/trade/{pair}/{interval}?from={_start_time}&to={_end_time}",
            request_type="GET",
            is_ohlc=True
        )['candles']

    def _get_earliest_timestamp(self, pair: str, interval: str):
        """
        Args:
            pair: Name of symbol pair
            interval: Binance Kline interval

        return:
            the earliest valid open timestamp
        """
        data = self._get_candles(
            pair=pair,
            interval='1w',
            start_time=1451624400000,
            end_time=int(time.time() * 1000),
        )
        return int(data[0]['time'])

    @staticmethod
    def _format_data(all_data: list, historical: bool = True) -> pd.DataFrame:
        """
        Args:
            all_data: output from _full_history

        Returns:
            standardized pandas dataframe
        """

        df = pd.DataFrame(all_data)

        df.columns = DATA_FORMATING['kraken']['columns']

        for var in DATA_FORMATING['kraken']['num_var']:
            df[var] = pd.to_numeric(df[var], downcast="float")

        if historical:
            df['next_open'] = df['open'].shift(-1)

        interval_ms = df['open_time'].iloc[1] - df['open_time'].iloc[0]

        df['close_time'] = df['open_time'] + interval_ms - 1

        for var in ['open_time', 'close_time']:
            df[var] = df[var].astype(int)

        return df.dropna()

    def get_historical_data(self, pair: str, interval: str, start_ts: int, end_ts: int) -> pd.DataFrame:
        """
        Args:
            pair: pair to get information from
            interval: granularity of the candle ['1m', '1h', ... '1d']
            start_ts: timestamp in milliseconds of the starting date
            end_ts: timestamp in milliseconds of the end date
        Returns:
            historical data requested in a standardized pandas dataframe
        """

        # init our list
        output_data = []

        # convert interval to useful value in seconds
        timeframe = interval_to_milliseconds(interval)

        # establish first available start timestamp
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
                output_data += temp_data

            # handle the case where exactly the limit amount of data was returned last loop
            # check if we received less than the required limit and exit the loop
            if not len(temp_data) or len(temp_data) < self.historical_limit:
                # exit the while loop
                break

            # increment next call by our timeframe
            start_time = temp_data[-1]['time'] + timeframe

            # exit loop if we reached end_ts before reaching <limit> klines
            if end_ts and start_time >= end_ts:
                break

            # sleep after every 3rd call to be kind to the API
            idx += 1
            if idx % 3 == 0:
                time.sleep(1)

        return self._format_data(all_data=output_data, historical=True)

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

