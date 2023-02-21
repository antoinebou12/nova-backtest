import numpy as np
from requests import Request, Session
import hmac
import urllib.parse as parse
import hashlib
import base64
import datetime
import pandas as pd
import time

from novalabs.utils.helpers import interval_to_milliseconds, retry_requests
from novalabs.clients.client_interface import BackTestClientInterface


class Huobi(BackTestClientInterface):

    def __init__(self,
                 key: str = '',
                 secret: str = '',
                 testnet: bool = False):

        self.api_key = key
        self.api_secret = secret

        self.based_endpoint = "https://api.hbdm.com"
        self._session = Session()

        self.historical_limit = 2000
        self.pairs_info = {}

    def generate_signature(self, method: str, request_path: str, _params: dict):

        sign_params = _params if _params else {}
        sign_params.update({
            "AccessKeyId": self.api_key,
            "SignatureMethod": "HmacSHA256",
            "SignatureVersion": "2",
            "Timestamp": datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S"),
        })
        sorted_params = sorted(sign_params.items(), key=lambda d: d[0], reverse=False)
        encode_params = parse.urlencode(sorted_params)
        host_url = self.based_endpoint.replace("https://", "")
        payload = [method, host_url, request_path, encode_params]
        payload = "\n".join(payload)
        hash_ = hmac.new(
            self.api_secret.encode(encoding="utf8"),
            payload.encode(encoding="UTF8"),
            digestmod=hashlib.sha256
        )
        signature = base64.b64encode(hash_.digest())
        sign_params['Signature'] = signature.decode()
        return sign_params

    @retry_requests
    def _send_request(self, end_point: str, request_type: str, params: dict = None, is_signed: bool = False):

        uri = f'{self.based_endpoint}{end_point}'

        if is_signed:
            _signed = self.generate_signature(request_type, end_point, params)
            request = Request(request_type, uri, params=_signed, json=params)
        else:
            request = Request(request_type, uri, params=params)

        prepared = request.prepare()
        prepared.headers['User-Agent'] = "NovaLabs"
        if request_type == "GET":
            prepared.headers['Content-Type'] = "application/x-www-form-urlencoded"
        else:
            prepared.headers["Accept"] = "application/json"
            prepared.headers['Content-Type'] = "application/json"
        response = self._session.send(prepared)
        return response.json()

    def get_server_time(self) -> int:

        ts = self._send_request(
            end_point='/api/v1/timestamp',
            request_type='GET'
        )['ts']

        return int(ts)

    def get_pairs_info(self,
                       quote_asset: str) -> dict:
        """
        Returns:
            All pairs available and tradable on the exchange.
        """
        contracts = self._send_request(
            end_point='/linear-swap-api/v1/swap_contract_info',
            request_type='GET',
            params={},
            is_signed=False
        )['data']

        pairs_info = {}

        for contract in contracts:
            tradable = contract['contract_status'] == 1

            if tradable and quote_asset == contract['trade_partition']:
                pairs_info[contract['contract_code']] = {}

                pairs_info[contract['contract_code']]['quote_asset'] = contract['trade_partition']

                pairs_info[contract['contract_code']]['maxQuantity'] = np.Inf
                pairs_info[contract['contract_code']]['minQuantity'] = np.Inf

                pairs_info[contract['contract_code']]['tick_size'] = contract['price_tick']
                if pairs_info[contract['contract_code']]['tick_size'] < 1:
                    step_size = str(contract['price_tick'])[::-1].find('.')
                    pairs_info[contract['contract_code']]['pricePrecision'] = int(step_size)
                else:
                    pairs_info[contract['contract_code']]['pricePrecision'] = 1

                pairs_info[contract['contract_code']]['step_size'] = contract['contract_size']

                if pairs_info[contract['contract_code']]['step_size'] < 1:
                    step_size = str(contract['contract_size'])[::-1].find('.')
                    pairs_info[contract['contract_code']]['quantityPrecision'] = int(step_size)
                else:
                    pairs_info[contract['contract_code']]['quantityPrecision'] = 1

        return pairs_info

    @staticmethod
    def _convert_interval(std_interval) -> str:
        mul = int(std_interval[:-1])

        if 'm' in std_interval:
            return f"{mul}min"

        elif 'h' in std_interval:
            return f"{mul}hour"

        elif 'd' in std_interval:
            return f"{mul}day"

    def _get_candles(self,
                     pair: str,
                     interval: str,
                     start_time: int,
                     limit: int = 2000,
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
        end_time = start_time + interval_to_milliseconds(interval=interval) * (limit - 1)

        params = {
            'contract_code': pair,
            'period': _interval,
            'from': start_time // 1000,
            'to': end_time // 1000
        }
        data = self._send_request(
            end_point=f"/linear-swap-ex/market/history/kline",
            request_type="GET",
            params=params
        )

        return data['data']

    def _get_earliest_timestamp(self, pair: str, interval: str) -> int:

        kline = []
        start_time = 1603152000000

        while len(kline) == 0:

            kline = self._get_candles(
                pair=pair,
                interval=interval,
                start_time=start_time,
                limit=2000
            )

            start_time += interval_to_milliseconds(interval=interval) * (2000 - 1)

        return kline[0]['id'] * 1000
    @staticmethod
    def _format_data(all_data: list, historical: bool = True) -> pd.DataFrame:
        """
        Args:
            all_data: output from _full_history

        Returns:
            standardized pandas dataframe
        """

        df = pd.DataFrame.from_records(all_data)

        df = df.rename(columns={"id": "open_time",
                                "amount": "volume",
                                "trade_turnover": "quote_asset_volume",
                                "count": "nb_of_trades"})

        df = df.drop(columns=['vol'])

        df['open_time'] = 1000 * df['open_time']

        if historical:
            df['next_open'] = df['open'].shift(-1)

        interval_ms = 1000 * (all_data[1]['id'] - all_data[0]['id'])
        df['close_time'] = df['open_time'] + interval_ms - 1

        return df

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
            start_ts = 1000 * temp_data[-1]['id'] + timeframe

            # exit loop if we reached end_ts before reaching <limit> klines
            if end_ts and start_ts >= end_ts:
                break

        df = self._format_data(all_data=klines)

        return df[df['open_time'] <= end_ts]

    def update_historical(self,
                          pair: str,
                          interval: str,
                          current_df: pd.DataFrame) -> pd.DataFrame:

        end_date_data_ts = current_df['open_time'].max()
        now_date_ts = int(time.time() * 1000)

        df = self.get_historical_data(pair=pair,
                                      interval=interval,
                                      start_ts=end_date_data_ts,
                                      end_ts=now_date_ts)

        return pd.concat([current_df, df], ignore_index=True).drop_duplicates(subset=['open_time'])