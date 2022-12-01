from novalabs.utils.helpers import interval_to_milliseconds
from novalabs.utils.constant import DATA_FORMATING
from requests import Request, Session
from urllib.parse import urlencode
import pandas as pd
import hashlib
import time
import hmac


class Binance:

    def __init__(self,
                 key: str,
                 secret: str,
                 testnet: bool
                 ):

        self.api_key = key
        self.api_secret = secret

        self.based_endpoint = "https://testnet.binancefuture.com" if testnet else "https://fapi.binance.com"

        self._session = Session()

        self.historical_limit = 1000

        self.pairs_info = self.get_pairs_info()

    # API REQUEST FORMAT
    def _send_request(self, end_point: str, request_type: str, params: dict = None, signed: bool = False):

        if params is None:
            params = {}
        if signed:

            params['timestamp'] = int(time.time() * 1000)
            query_string = urlencode(params, True).replace("%40", "@")
            m = hmac.new(self.api_secret.encode("utf-8"), query_string.encode("utf-8"), hashlib.sha256)
            params['signature'] = m.hexdigest()

        request = Request(request_type, f'{self.based_endpoint}{end_point}',
                          params=urlencode(params, True).replace("%40", "@"))

        prepared = request.prepare()
        prepared.headers['Content-Type'] = "application/json;charset=utf-8"
        prepared.headers['User-Agent'] = "NovaLabs"
        prepared.headers['X-MBX-APIKEY'] = self.api_key
        response = self._session.send(prepared)
        data = response.json()

        if isinstance(data, dict) and 'code' in data.keys() and data['code'] not in [200, -2011]:
            print(f'##### ERROR : {data["msg"]} #####')

        return data

    def get_server_time(self) -> int:
        """
        Returns:
            the timestamp in milliseconds
        """
        data = self._send_request(
            end_point=f"/fapi/v1/time",
            request_type="GET"
        )
        return int(data['serverTime'])

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
        _limit = limit if limit else self.historical_limit
        _params = {
            "symbol": pair,
            "interval": interval,
            "startTime": start_time,
            "endTime": end_time,
            "limit": _limit
        }
        return self._send_request(
            end_point=f"/fapi/v1/klines",
            request_type="GET",
            params=_params
        )

    def _get_earliest_timestamp(self, pair: str, interval: str):
        """
        Args:
            pair: Name of symbol pair
            interval: Binance Kline interval

        return:
            the earliest valid open timestamp
        """
        kline = self._get_candles(
            pair=pair,
            interval=interval,
            start_time=0,
            end_time=int(time.time() * 1000),
            limit=1
        )
        return kline[0][0]

    @staticmethod
    def _format_data(all_data: list, historical: bool = True) -> pd.DataFrame:
        """
        Args:
            all_data: output from _full_history

        Returns:
            standardized pandas dataframe
        """

        df = pd.DataFrame(all_data, columns=DATA_FORMATING['binance']['columns'])

        for var in DATA_FORMATING['binance']['num_var']:
            df[var] = pd.to_numeric(df[var], downcast="float")

        for var in DATA_FORMATING['binance']['date_var']:
            df[var] = pd.to_numeric(df[var], downcast="integer")

        if historical:
            df['next_open'] = df['open'].shift(-1)

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

        # if a start time was passed convert it
        start_ts = start_ts

        # establish first available start timestamp
        first_valid_ts = self._get_earliest_timestamp(
            pair=pair,
            interval=interval
        )
        start_ts = max(start_ts, first_valid_ts)

        # if an end time was passed convert it
        end_ts = end_ts

        if end_ts and start_ts and end_ts <= start_ts:
            return pd.DataFrame()

        idx = 0
        while True:
            # fetch the klines from start_ts up to max 500 entries or the end_ts if set
            temp_data = self._get_candles(
                pair=pair,
                interval=interval,
                limit=self.historical_limit,
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
            start_ts = temp_data[-1][0] + timeframe

            # exit loop if we reached end_ts before reaching <limit> klines
            if end_ts and start_ts >= end_ts:
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

        end_date_data_ts = int(current_df['open_time'].max())
        now_date_ts = int(time.time() * 1000)
        df = self.get_historical_data(
            pair=pair,
            interval=interval,
            start_ts=end_date_data_ts,
            end_ts=now_date_ts
        )
        return pd.concat([current_df, df], ignore_index=True).drop_duplicates(subset=['open_time'])

    def get_pairs_info(self) -> dict:
        """
        Note: This output is used for standardization purpose because binance order api has
        decimal restriction per pair.
        Returns:
            a dict where the key is equal to the pair symbol and the value is a dict that contains
            the following information "quantityPrecision" and "quantityPrecision".
        """
        info = self._send_request(
            end_point=f"/fapi/v1/exchangeInfo",
            request_type="GET",
        )

        output = {}

        for symbol in info['symbols']:
            if symbol['contractType'] == 'PERPETUAL':

                pair = symbol['symbol']

                output[pair] = {}
                output[pair]['quote_asset'] = symbol['quoteAsset']

                for fil in symbol['filters']:
                    if fil['filterType'] == 'PRICE_FILTER':
                        output[pair]['tick_size'] = float(fil['tickSize'])

                        if output[pair]['tick_size'] < 1:
                            tick_size = int(str(fil['tickSize'])[::-1].find('.'))
                            output[pair]['pricePrecision'] = int(min(tick_size, symbol['pricePrecision']))
                        else:
                            output[pair]['pricePrecision'] = int(symbol['pricePrecision'])

                    if fil['filterType'] == 'LOT_SIZE':
                        output[pair]['step_size'] = float(fil['stepSize'])

                        if output[pair]['step_size'] < 1:
                            step_size = int(str(fil['stepSize'])[::-1].find('.'))
                            output[pair]['quantityPrecision'] = int(min(step_size, symbol['quantityPrecision']))
                        else:
                            output[pair]['quantityPrecision'] = int(symbol['quantityPrecision'])

                        output[pair]['minQuantity'] = float(fil['minQty'])
                        output[pair]['maxQuantity'] = float(fil['maxQty'])

        return output