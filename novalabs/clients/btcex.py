from novalabs.utils.helpers import interval_to_milliseconds, retry_requests
from novalabs.utils.constant import DATA_FORMATING
from novalabs.clients.client_interface import BackTestClientInterface
from requests import Request, Session
from urllib.parse import urlencode
import time
import pandas as pd
import numpy as np


class BTCEX(BackTestClientInterface):

    def __init__(self,
                 key: str = "",
                 secret: str = "",
                 testnet: bool = False):

        self.api_key = key
        self.api_secret = secret

        self.based_endpoint = "" if testnet else "https://api.btcex.com/api/v1"

        self._session = Session()

        self.historical_limit = 10_000

        self.access_token = ''
        self.refresh_token = ''
        self.end_connection_date = np.Inf
        self.connected = False
        if key != '' and secret != '':
            self.connect()

        self.pairs_info = {}

    # API REQUEST FORMAT
    @retry_requests
    def _send_request(self,
                      end_point: str,
                      request_type: str,
                      params: dict = None,
                      signed: bool = False):

        if self.connected and self.end_connection_date - time.time() < 86400:
            self.connected = False

            self.refresh_connection()

        if params is None:
            params = {}

        if request_type == 'POST':
            request = Request(request_type, f'{self.based_endpoint}{end_point}',
                              json=params)
        elif request_type == 'GET':
            request = Request(request_type, f'{self.based_endpoint}{end_point}',
                              params=urlencode(params, True))
        else:
            raise ValueError("Please enter valid request_type")

        prepared = request.prepare()
        if signed:
            prepared.headers['Authorization'] = f"bearer {self.access_token}"

        response = self._session.send(prepared,
                                      timeout=5)

        data = response.json()

        if 'error' in data.keys():
            raise ConnectionError(data['error'])

        return data

    def connect(self):

        params = {'grant_type': 'client_credentials',
                  'client_id': self.api_key,
                  'client_secret': self.api_secret}

        data = self._send_request(
            end_point=f"/public/auth",
            request_type="GET",
            params=params,
        )['result']

        self.access_token = data['access_token']
        self.refresh_token = data['refresh_token']
        self.end_connection_date = int(time.time()) + data['expires_in']
        self.connected = True

    def logout(self):

        data = self._send_request(
            end_point=f"/private/logout",
            request_type="GET",
            signed=True
        )['result']

        return data

    def refresh_connection(self):

        params = {'grant_type': 'refresh_token',
                  'refresh_token': self.refresh_token}

        data = self._send_request(
            end_point=f"/public/auth",
            request_type="GET",
            params=params,
        )['result']

        self.access_token = data['access_token']
        self.refresh_token = data['refresh_token']
        self.end_connection_date = int(time.time()) + data['expires_in']
        self.connected = True

    def get_server_time(self) -> int:
        """
        Returns:
            the timestamp in milliseconds
        """
        ts = self._send_request(
            end_point=f"/public/ping",
            request_type="GET",
            signed=False,
        )['usOut']
        return int(ts)

    def get_pairs_info(self,
                       quote_asset: str) -> dict:

        pairs_info = {}

        data = self._send_request(
            end_point=f"/public/get_instruments",
            params={'currency': 'PERPETUAL'},
            request_type="GET"
        )['result']

        for info in data:
            if info['is_active'] and info['base_currency'] == quote_asset:
                pair_name = info['instrument_name']
                pairs_info[pair_name] = {}

                pairs_info[pair_name]['quote_asset'] = info['base_currency']

                pairs_info[pair_name]['maxLimitQuantity'] = np.Inf
                pairs_info[pair_name]['maxMarketQuantity'] = np.Inf
                pairs_info[pair_name]['minQuantity'] = float(info['min_qty'])

                pairs_info[pair_name]['tick_size'] = float(info['tick_size'])
                pairs_info[pair_name]['step_size'] = float(info['min_trade_amount'])

                pairs_info[pair_name]['creation_timestamp'] = int(info['creation_timestamp'])

        return pairs_info

    @staticmethod
    def _convert_interval(std_interval) -> str:
        """
        Args:
            std_interval: Binance's interval format
        Returns:
            Bybit's interval format
        """

        if 'm' in std_interval:
            return std_interval[:-1]

        elif 'h' in std_interval:
            mul = int(std_interval[:-1])
            return str(60 * mul)
        else:
            return std_interval[-1].upper()

    def _get_candles(self,
                     pair: str,
                     interval: str,
                     start_time: int,
                     end_time: int = None,
                     limit: int = None) -> list:

        """

        Args:
            pair: pair to get the candles
            interval: Data refresh interval. Enum : 1 3 5 15 30 60 120 240 360 720 "D" "M" "W"
            start_time: From timestamp in milliseconds
            limit: Limit for data size per page, max size is 200. Default as showing 200 pieces of data per page

        Returns:
            list of candles
        """

        _interval = self._convert_interval(std_interval=interval)

        params = {
            'instrument_name': pair,
            'resolution': _interval,
            'start_timestamp': start_time // 1000,
            'end_timestamp': end_time // 1000
        }
        data = self._send_request(
            end_point=f"/public/get_tradingview_chart_data",
            request_type="GET",
            params=params
        )['result']

        return data

    def _get_earliest_timestamp(self, pair: str, interval: str = None) -> int:

        return int(self.pairs_info[pair]['creation_timestamp'])

    @staticmethod
    def _format_data(all_data: list, historical: bool = True) -> pd.DataFrame:
        """
        Args:
            all_data: output from _full_history

        Returns:
            standardized pandas dataframe
        """

        interval_ms = 1000 * (all_data[1]['tick'] - all_data[0]['tick'])
        df = pd.DataFrame(all_data)[DATA_FORMATING['btcex']['columns']]

        for var in DATA_FORMATING['btcex']['num_var']:
            df[var] = pd.to_numeric(df[var], downcast="float")

        df = df.rename(columns={'tick': 'open_time'})

        df['open_time'] = 1000 * df['open_time']

        if historical:
            df['next_open'] = df['open'].shift(-1)

        df['close_time'] = df['open_time'] + interval_ms - 1

        return df.dropna()

    def get_historical_data(self,
                            pair: str,
                            interval: str,
                            start_ts: int,
                            end_ts: int) -> pd.DataFrame:
        """
        Args:
            pair: pair to get data from
            interval: granularity of the candle ['1m', '1h', ... '1d']
            start_ts: timestamp in milliseconds of the starting date
            end_ts: timestamp in milliseconds of the end date
        Returns:
            the complete raw data history desired -> multiple requested could be executed
        """

        # init our list
        klines = []

        # convert interval to useful value in ms
        timeframe = interval_to_milliseconds(interval)

        # establish first available start timestamp
        if start_ts is not None:
            first_valid_ts = self._get_earliest_timestamp(
                pair=pair,
            )
            start_ts = max(start_ts, first_valid_ts)

        if end_ts and start_ts and end_ts <= start_ts:
            raise ValueError('end_ts must be greater than start_ts')

        while True:
            # fetch the klines from start_ts up to max 500 entries or the end_ts if set
            temp_data = self._get_candles(
                pair=pair,
                interval=interval,
                start_time=start_ts,
                end_time=start_ts + self.historical_limit * timeframe
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
            start_ts = 1000 * temp_data[-1]['tick'] + timeframe

            # exit loop if we reached end_ts before reaching <limit> klines
            if end_ts and start_ts >= end_ts:
                break

        df = self._format_data(all_data=klines)

        return df[df['open_time'] <= end_ts]

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
        now_date_ts = int(time.time() * 1000)

        df_temp = self.get_historical_data(pair=pair,
                                           interval=interval,
                                           start_ts=end_date_data_ts,
                                           end_ts=now_date_ts)

        return pd.concat([current_df, df_temp], ignore_index=True).drop_duplicates(subset=['open_time'])