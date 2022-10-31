from requests import Request, Session
import hmac
import base64
import time
import hashlib
from nova.utils.helpers import interval_to_milliseconds
from datetime import datetime, date
import pandas as pd
from nova.utils.constant import DATA_FORMATING
import asyncio
import aiohttp


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

        self.historical_limit = 290

    def _send_request(self, end_point: str, request_type: str, params: dict = None, signed: bool = False):

        timestamp = str(time.time())

        to_use = "https://api.pro.coinbase.com" if not signed else self.based_endpoint
        request = Request(request_type, f'{to_use}{end_point}', params=params)
        prepared = request.prepare()

        prepared.headers['Content-Type'] = "application/json"

        if signed:
            _params = ""
            if params is not None:
                _params = params
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
                pairs_info[pair['id']]['pricePrecision'] = 7
                pairs_info[pair['id']]['maxQuantity'] = float('inf')
                pairs_info[pair['id']]['minQuantity'] = 0.0
                pairs_info[pair['id']]['tick_size'] = float(pair['base_increment'])
                pairs_info[pair['id']]['quantityPrecision'] = str(pair['base_increment'])[::-1].find('.')

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

        _start_time = datetime.fromtimestamp(int(start_time // 1000))
        _end_time = datetime.fromtimestamp(int(end_time // 1000))
        _interval = str(int(interval_to_milliseconds(interval)//1000))

        return self._send_request(
            end_point=f'/products/{pair}/candles',
            request_type="GET",
            params={
                'start': _start_time.isoformat(),
                'end': _end_time.isoformat(),
                'granularity': _interval
            }
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

        start_year = 2018

        while start_year <= date.today().year:

            kline = self._get_candles(
                pair=pair,
                interval=interval,
                start_time=int(datetime(start_year, 1, 1).timestamp() * 1000),
                end_time=int(datetime(start_year, 1, 2).timestamp() * 1000),
            )

            instance_type = isinstance(kline, dict)

            if instance_type:
                start_year += 1
            elif not instance_type and len(kline) == 0:
                start_year += 1
            else:
                print(f'Earliest Year Extracted for {pair} : {datetime(start_year, 1, 1)}')
                return kline[0][0] * 1000

        print(f'Earliest Year is after the beginning of the year')
        return 0

    @staticmethod
    def _format_data(all_data: list, historical: bool = True) -> pd.DataFrame:
        """
        Args:
            all_data: output from _full_history

        Returns:
            standardized pandas dataframe
        """

        df = pd.DataFrame(all_data, columns=DATA_FORMATING['coinbase']['columns'])
        df['open_time'] = df['open_time'] * 1000
        interval_ms = df['open_time'].iloc[1] - df['open_time'].iloc[0]
        df['close_time'] = df['open_time'] + interval_ms - 1

        for var in DATA_FORMATING['coinbase']['num_var']:
            df[var] = pd.to_numeric(df[var], downcast="float")

        for var in DATA_FORMATING['coinbase']['date_var']:
            df[var] = pd.to_numeric(df[var], downcast="integer")

        if historical:
            df['next_open'] = df['open'].shift(-1)

        return df.dropna().drop_duplicates()

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
            start_time = temp_data[0][0] * 1000 + timeframe

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

    def setup_account(self, quote_asset: str,
                      leverage: int, bankroll: float, max_down: float, list_pairs: list):

        data = self._send_request(
            end_point=f"/accounts",
            request_type="GET",
            signed=True
        )

        balance = 0

        for info in data:
            if info['currency'] == quote_asset:
                assert info['trading_enabled']
                balance = float(info['available'])

        assert balance >= bankroll * (1 + max_down), f"The account has only {round(balance, 2)} {quote_asset}. " \
                                                     f"{round(bankroll * (1 + max_down), 2)} {quote_asset} is required"

    async def get_prod_candles(
            self,
            session,
            pair,
            interval,
            window,
            current_pair_state: dict = None
    ):

        url = f"https://api.pro.coinbase.com/products/{pair}/candles"

        final_dict = {}
        final_dict[pair] = {}

        timeframe = int(interval_to_milliseconds(interval))

        if current_pair_state is not None:
            start_time = int(current_pair_state[pair]['latest_update']) - timeframe
        else:
            start_time = int(time.time() - (window + 1) * (timeframe // 1000)) * 1000

        end_t = start_time + timeframe * self.historical_limit

        _start_time = datetime.fromtimestamp(int(start_time // 1000))
        _end_time = datetime.fromtimestamp(int(end_t // 1000))
        _interval = str(int(timeframe//1000))

        params = {
                'start': _start_time.isoformat(),
                'end': _end_time.isoformat(),
                'granularity': _interval
            }

        # Compute the server time
        s_time = int(1000 * time.time())

        async with session.get(url=url, params=params) as response:
            data = await response.json()
            df = self._format_data(data['result'], historical=False)

            df = df[df['close_time'] < s_time]

            latest_update = df['open_time'].values[-1]

            for var in ['open_time', 'close_time']:
                df[var] = pd.to_datetime(df[var], unit='ms')

            if current_pair_state is None:
                final_dict[pair]['latest_update'] = latest_update
                final_dict[pair]['data'] = df

            else:
                df_new = pd.concat([current_pair_state[pair]['data'], df])
                df_new = df_new.drop_duplicates(subset=['open_time']).sort_values(
                    by=['open_time'],
                    ascending=True
                )
                df_new = df_new.tail(window)
                df_new = df_new.reset_index(drop=True)

                final_dict[pair]['latest_update'] = latest_update
                final_dict[pair]['data'] = df_new

            return final_dict

    async def get_prod_data(
            self,
            list_pair: list,
            interval: str,
            nb_candles: int,
            current_state: dict
    ):
        """
        Note: This function is called once when the bot is instantiated.
        This function execute n API calls with n representing the number of pair in the list
        Args:
            list_pair: list of all the pairs you want to run the bot on.
            interval: time interval
            nb_candles: number of candles needed
            current_state: boolean indicate if this is an update
        Returns: None, but it fills the dictionary self.prod_data that will contain all the data
        needed for the analysis.
        !! Command to run async function: asyncio.run(self.get_prod_data(list_pair=list_pair)) !!
        """

        # If we need more than 200 candles (which is the API's limit) we call self.get_historical_data instead
        if nb_candles > self.historical_limit and current_state is None:

            final_dict = {}

            for pair in list_pair:
                final_dict[pair] = {}
                start_time = int(1000 * time.time() - (nb_candles + 1) * interval_to_milliseconds(interval=interval))
                last_update = int(1000 * time.time())

                print(start_time, last_update)

                df = self.get_historical_data(
                    pair=pair,
                    start_ts=start_time,
                    interval=interval,
                    end_ts=last_update
                )

                df = df[df['close_time'] < last_update]
                latest_update = df['open_time'].values[-1]
                for var in ['open_time', 'close_time']:
                    df[var] = pd.to_datetime(df[var], unit='ms')

                final_dict[pair]['latest_update'] = latest_update
                final_dict[pair]['data'] = df

            return final_dict

        async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=False)) as session:
            tasks = []
            for pair in list_pair:
                task = asyncio.ensure_future(
                    self.get_prod_candles(
                        session=session,
                        pair=pair,
                        interval=interval,
                        window=nb_candles,
                        current_pair_state=current_state)
                )
                tasks.append(task)
            all_info = await asyncio.gather(*tasks)

            all_data = {}
            for info in all_info:
                all_data.update(info)
            return all_data



