from novalabs.utils.helpers import interval_to_milliseconds
from novalabs.utils.constant import DATA_FORMATING
from requests import Request, Session
from urllib.parse import urlencode
import hashlib
import time
import hmac
import json
import pandas as pd


class Bybit:

    def __init__(self,
                 key: str,
                 secret: str,
                 testnet: bool = False):

        self.api_key = key
        self.api_secret = secret

        self.based_endpoint = "https://api-testnet.bybit.com" if testnet else "https://api.bybit.com"

        self._session = Session()

        self.historical_limit = 200

        self.pairs_info = self.get_pairs_info()

    # API REQUEST FORMAT
    def _send_request(self, end_point: str, request_type: str, params: dict = None, signed: bool = False):

        if params is None:
            params = {}

        if signed:
            params['api_key'] = self.api_key
            params['timestamp'] = int(time.time() * 1000)
            params = dict(sorted(params.items()))

            query_string = urlencode(params, True)
            query_string = query_string.replace('False', 'false').replace('True', 'true')

            m = hmac.new(self.api_secret.encode("utf-8"), query_string.encode("utf-8"), hashlib.sha256)
            params['sign'] = m.hexdigest()

        if request_type == 'POST':
            request = Request(request_type, f'{self.based_endpoint}{end_point}',
                              data=json.dumps(params))
        elif request_type == 'GET':
            request = Request(request_type, f'{self.based_endpoint}{end_point}',
                              params=urlencode(params, True))
        else:
            raise ValueError("Please enter valid request_type")

        prepared = request.prepare()
        prepared.headers['Content-Type'] = "application/json"
        response = self._session.send(prepared)
        data = response.json()

        if data['ret_msg'] != "OK" and data['ret_code'] != 20001:
            print(f"{data['ret_code']} : {data['ret_msg']}")

        return data

    def get_server_time(self) -> int:
        """
        Returns:
            the timestamp in milliseconds
        """
        ts = self._send_request(
            end_point=f"/v2/public/time",
            request_type="GET"
        )['time_now']
        return int(float(ts) * 1000)

    def _get_candles(self,
                     pair: str,
                     interval: str,
                     start_time: int,
                     limit: int = 200,
                     end_time: int = None) -> list:

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
            'symbol': pair,
            'interval': _interval,
            'from': start_time // 1000,
            'limit': limit
        }
        data = self._send_request(
            end_point=f"/public/linear/kline",
            request_type="GET",
            params=params
        )
        return data['result']

    def get_pairs_info(self) -> dict:
        """
        Returns:
            All pairs available and tradable on the exchange.
        """
        data = self._send_request(
            end_point=f"/v2/public/symbols",
            request_type="GET"
        )['result']

        pairs_info = {}

        for pair in data:
            tradable = pair['status'] == 'Trading'

            if tradable:
                pairs_info[pair['name']] = {}
                pairs_info[pair['name']]['quote_asset'] = pair['quote_currency']

                pairs_info[pair['name']]['maxQuantity'] = float(pair['lot_size_filter']['max_trading_qty'])
                pairs_info[pair['name']]['minQuantity'] = float(pair['lot_size_filter']['min_trading_qty'])

                pairs_info[pair['name']]['tick_size'] = float(pair['price_filter']['tick_size'])
                pairs_info[pair['name']]['pricePrecision'] = pair['price_scale']

                pairs_info[pair['name']]['step_size'] = float(pair['lot_size_filter']['qty_step'])

                if float(pair['lot_size_filter']['qty_step']) < 1:
                    step_size = str(pair['lot_size_filter']['qty_step'])[::-1].find('.')
                    pairs_info[pair['name']]['quantityPrecision'] = int(step_size)
                else:
                    pairs_info[pair['name']]['quantityPrecision'] = 1

        return pairs_info

    def _get_earliest_timestamp(self, pair: str, interval: str) -> int:
        """
        Args:
            pair: Name of symbol pair -- BNBBTC
            interval: Binance Kline interval

        return:
            the earliest valid open timestamp
        """

        kline = self._get_candles(
            pair=pair,
            interval=interval,
            start_time=1467900800000,
            limit=1
        )

        return kline[0]['open_time'] * 1000

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

    @staticmethod
    def _format_data(all_data: list, historical: bool = True) -> pd.DataFrame:
        """
        Args:
            all_data: output from _full_history

        Returns:
            standardized pandas dataframe
        """

        interval_ms = 1000 * (all_data[1]['start_at'] - all_data[0]['start_at'])
        df = pd.DataFrame(all_data)[DATA_FORMATING['bybit']['columns']]

        for var in DATA_FORMATING['bybit']['num_var']:
            df[var] = pd.to_numeric(df[var], downcast="float")

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
                interval=interval
            )
            start_ts = max(start_ts, first_valid_ts)

        if end_ts and start_ts and end_ts <= start_ts:
            raise ValueError('end_ts must be greater than start_ts')

        while True:
            # fetch the klines from start_ts up to max 500 entries or the end_ts if set
            temp_data = self._get_candles(
                pair=pair,
                interval=interval,
                limit=self.historical_limit,
                start_time=start_ts
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
            start_ts = 1000 * temp_data[-1]['open_time'] + timeframe

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

        df = self.get_historical_data(pair=pair,
                                      interval=interval,
                                      start_ts=end_date_data_ts,
                                      end_ts=now_date_ts)

        return pd.concat([current_df, df], ignore_index=True).drop_duplicates(subset=['open_time'])
