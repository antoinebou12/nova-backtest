from requests import Request, Session
import hmac
import base64
import json
from datetime import datetime
from novalabs.utils.helpers import interval_to_milliseconds
import time
from novalabs.utils.constant import DATA_FORMATING
import pandas as pd
import numpy as np
from typing import Union


class OKX:

    def __init__(self,
                 key: str,
                 secret: str,
                 pass_phrase: str,
                 testnet: bool):

        self.api_key = key
        self.api_secret = secret
        self.pass_phrase = pass_phrase

        self.based_endpoint = "https://www.okx.com"
        self._session = Session()

        self.quote_asset = 'USDT'

        self.pairs_info = self.get_pairs_info()

        self.historical_limit = 90

    def _send_request(self, end_point: str, request_type: str, params: Union[dict, list] = None, signed: bool = False):

        now = datetime.utcnow()
        timestamp = now.isoformat("T", "milliseconds") + "Z"

        request = Request(request_type, f'{self.based_endpoint}{end_point}', data=json.dumps(params))
        prepared = request.prepare()

        if signed:
            body = ""
            if params:
                body = json.dumps(params)
                prepared.body = body

            to_hash = str(timestamp) + str.upper(request_type) + end_point + body

            mac = hmac.new(bytes(self.api_secret, encoding='utf8'),
                           bytes(to_hash, encoding='utf-8'),
                           digestmod='sha256')

            signature = base64.b64encode(mac.digest())

            prepared.headers['OK-ACCESS-KEY'] = self.api_key
            prepared.headers['OK-ACCESS-SIGN'] = signature
            prepared.headers['OK-ACCESS-PASSPHRASE'] = self.pass_phrase

        prepared.headers['Content-Type'] = "application/json"
        prepared.headers['OK-ACCESS-TIMESTAMP'] = timestamp

        response = self._session.send(prepared)

        return response.json()

    def get_server_time(self) -> int:
        """
        Note: FTX does not have any server time end point so we are simulating it with the time function
        Returns:
            the timestamp in milliseconds
        """
        return int(self._send_request(
            end_point=f"/api/v5/public/time",
            request_type="GET",
        )['data'][0]['ts'])

    def get_pairs_info(self) -> dict:

        data = self._send_request(
            end_point=f"/api/v5/public/instruments?instType=SWAP",
            request_type="GET"
        )['data']

        pairs_info = {}

        for pair in data:

            if pair['settleCcy'] == self.quote_asset and pair['state'] == 'live' and pair['instType'] == 'SWAP' and pair['ctType'] == 'linear':

                pairs_info[pair['instId']] = {}

                pairs_info[pair['instId']]['based_asset'] = pair['ctValCcy']
                pairs_info[pair['instId']]['quote_asset'] = pair['settleCcy']

                size_increment = np.format_float_positional(float(pair["lotSz"]), trim='-')
                price_increment = np.format_float_positional(float(pair["tickSz"]), trim='-')

                pairs_info[pair['instId']]['maxQuantity'] = float('inf')
                pairs_info[pair['instId']]['minQuantity'] = float(pair['minSz'])

                price_precision = int(str(price_increment)[::-1].find('.')) if float(pair['tickSz']) < 1 else 1
                pairs_info[pair['instId']]['tick_size'] = float(pair['tickSz'])
                pairs_info[pair['instId']]['pricePrecision'] = price_precision

                qty_precision = int(str(size_increment)[::-1].find('.')) if float(pair['minSz']) < 1 else 1
                pairs_info[pair['instId']]['step_size'] = float(pair['minSz'])
                pairs_info[pair['instId']]['quantityPrecision'] = qty_precision

                pairs_info[pair['instId']]['earliest_timestamp'] = int(pair['listTime'])

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
        _end_time = start_time + interval_to_milliseconds(interval) * self.historical_limit
        _bar = interval if 'm' in interval else interval.upper()
        _endpoint = f"/api/v5/market/history-candles?instId={pair}&bar={_bar}&before={start_time}&after={_end_time}"
        return self._send_request(
            end_point=_endpoint,
            request_type="GET",
        )['data']

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

        return self.pairs_info[pair]['earliest_timestamp']

    @staticmethod
    def _format_data(all_data: list, historical: bool = True) -> pd.DataFrame:
        """
        Args:
            all_data: output from _full_history

        Returns:
            standardized pandas dataframe
        """

        df = pd.DataFrame(all_data, columns=DATA_FORMATING['okx']['columns'])
        df = df.sort_values(by='open_time').reset_index(drop=True)

        for var in DATA_FORMATING['okx']['num_var']:
            df[var] = pd.to_numeric(df[var], downcast="float")

        for var in ['open_time']:
            df[var] = df[var].astype(int)

        df = df.sort_values(by='open_time').reset_index(drop=True)

        if historical:
            df['next_open'] = df['open'].shift(-1)

        interval_ms = df.loc[1, 'open_time'] - df.loc[0, 'open_time']

        df['close_time'] = df['open_time'] + interval_ms - 1

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

            end_t = int(start_time + timeframe * self.historical_limit)
            end_time = min(end_t, end_ts)

            # fetch the klines from start_ts up to max 500 entries or the end_ts if set
            temp_data = self._get_candles(
                pair=pair,
                interval=interval,
                start_time=start_time,
                end_time=end_time
            )

            if len(temp_data) == 0:
                break

            # append this loops data to our output data
            if temp_data:
                klines += temp_data

            # handle the case where exactly the limit amount of data was returned last loop
            # check if we received less than the required limit and exit the loop

            # increment next call by our timeframe
            start_time = int(temp_data[0][0])

            # exit loop if we reached end_ts before reaching <limit> klines
            if start_time >= end_ts:
                break

            # sleep after every 3rd call to be kind to the API
            idx += 1
            if idx % 5 == 0:
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
