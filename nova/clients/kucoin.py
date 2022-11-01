from requests import Request, Session
import hmac
import base64
import json
import time
import hashlib
from nova.utils.helpers import interval_to_minutes, interval_to_milliseconds, interval_to_minutes_str
from nova.utils.constant import DATA_FORMATING
import pandas as pd
from datetime import datetime
from typing import Union
import uuid


class Kucoin:

    def __init__(self,
                 key: str,
                 secret: str,
                 pass_phrase: str,
                 testnet: bool):
        self.api_key = key
        self.api_secret = secret
        self.pass_phrase = pass_phrase

        self.based_endpoint = "https://api-sandbox-futures.kucoin.com" if testnet else "https://api-futures.kucoin.com"

        self._session = Session()

        self.historical_limit = 190

        self.pairs_info = self.get_pairs_info()

        self.leverage = 2

    def _send_request(self, end_point: str, request_type: str, params: dict = {}, signed: bool = False):

        to_use = "https://api-futures.kucoin.com" if not signed else self.based_endpoint
        # to_use = "https://api-futures.kucoin.com" if not signed else "https://api-futures.kucoin.com"

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
            print(sig_str)
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
                pairs_info[pair['symbol']] = {}
                pairs_info[pair['symbol']]['quote_asset'] = pair['quoteCurrency']
                pairs_info[pair['symbol']]['pricePrecision'] = str(pair['tickSize'])[::-1].find('.')
                pairs_info[pair['symbol']]['maxQuantity'] = pair['maxOrderQty']
                pairs_info[pair['symbol']]['minQuantity'] = 0
                pairs_info[pair['symbol']]['tick_size'] = pair['tickSize']
                pairs_info[pair['symbol']]['quantityPrecision'] = 7
                pairs_info[pair['symbol']]['earliest_time'] = pair['firstOpenDate']

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
        _interval = interval_to_minutes_str(interval)
        _start_time = int(start_time // 1000)
        _end_time = int(end_time // 1000)

        _endpoint = f"/api/v1/market/candles?symbol={pair}&type={_interval}&startAt={_start_time}&endAt={_end_time}"

        return self._send_request(
            end_point=f'{_endpoint}',
            request_type="GET",
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

        return self.pairs_info[pair]['earliest_time']

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

        if historical:
            df['next_open'] = df['open'].shift(-1)

        interval_ms = df['open_time'].iloc[1] - df['open_time'].iloc[0]

        df['close_time'] = df['open_time'] + interval_ms - 1

        for var in ['open_time', 'close_time']:
            df[var] = df[var].astype(int)

        return df.dropna()

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

            print(start_time, end_time)

            # fetch the klines from start_ts up to max 500 entries or the end_ts if set
            temp_data = self._get_candles(
                pair=pair,
                interval=interval,
                start_time=start_time,
                end_time=end_time
            )

            print(temp_data)

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

    def setup_account(self, quote_asset: str, leverage: int, bankroll: float, max_down: float, list_pairs: list):

        self.leverage = leverage

        account_info = self._send_request(
            end_point=f"/api/v1/account-overview?currency={quote_asset}",
            request_type="GET",
            params={"currency": quote_asset},
            signed=True
        )['data']

        balance = account_info['availableBalance']

        assert balance >= bankroll * (1 + max_down), f"The account has only {round(balance, 2)} {quote_asset}. " \
                                                     f"{round(bankroll * (1 + max_down), 2)} {quote_asset} is required"

    def get_actual_positions(self, pairs: Union[list, str]) -> dict:
        """
        Args:
            pairs: list of pair that we want to run analysis on
        Returns:
            a dictionary containing all the current OPEN positions
        """

        _end_point = '/api/v1/positions'

        if isinstance(pairs, str):
            _end_point = f'/api/v1/position?symbol={pairs}'
            pairs = [pairs]

        all_pos = self._send_request(
            end_point=f"/api/v1/positions",
            request_type="GET",
            signed=True
        )['data']

        if isinstance(all_pos, dict):
            all_pos = [all_pos]

        position = {}

        # for pos in all_pos:
        #
        #     if pos['symbol'] in pairs and pos['currentQty'] != 0:
        #         position[pos['symbol']] = {}
        #         position[pos['symbol']]['position_size'] = abs(float(pos['currentQty']))
        #         position[pos['symbol']]['entry_price'] = float(pos['avgEntryPrice'])
        #         position[pos['symbol']]['unrealized_pnl'] = float(pos['unrealisedPnl'])
        #         position[pos['symbol']]['type_pos'] = 'LONG' if float(pos['netSize']) > 0 else 'SHORT'
        #         position[pos['future']]['exit_side'] = 'SELL' if float(pos['netSize']) > 0 else 'BUY'

        return all_pos

    def enter_market_order(self, pair: str, type_pos: str, quantity: float):

        """
            Args:
                pair: pair id that we want to create the order for
                type_pos: could be 'LONG' or 'SHORT'
                quantity: quantity should respect the minimum precision

            Returns:
                standardized output
        """

        side = 'buy' if type_pos == 'LONG' else 'sell'

        _params = {
            "clientOid": str(uuid.uuid4()),
            "symbol": pair,
            "side": side,
            "size": float(round(quantity, self.pairs_info[pair]['quantityPrecision'])),
            "type": "market",
            "leverage": str(self.leverage)
        }

        return self._send_request(
            end_point=f"/api/v1/orders",
            request_type="POST",
            params=_params,
            signed=True
        )