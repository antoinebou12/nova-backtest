from nova.clients.helpers import interval_to_milliseconds, convert_ts_str, get_timestamp
import time
from requests import Request, Session
from binance.um_futures import UMFutures
import hmac


class Binance:

    def __init__(self,
                 key: str,
                 secret: str):
        self.client = UMFutures(key=key, secret=secret)

        self.based_endpoint = "https://fapi.binance.com"
        self._session = Session()

        self.historical_limit = 1000
        self.pair_info = self._get_pair_info()

    # API REQUEST FORMAT
    def _create_request(self, end_point: str, request_type: str, **kwargs):
        ts = get_timestamp()
        request = Request(request_type, f'{self.based_endpoint}{end_point}', **kwargs)
        prepared = request.prepare()
        signature_payload = f'{ts}{prepared.method}{prepared.path_url}'.encode()
        if prepared.body:
            signature_payload += prepared.body
        signature = hmac.new(self.api_secret.encode(), signature_payload, 'sha256').hexdigest()
        prepared.headers['FTX-KEY'] = self.api_key
        prepared.headers['FTX-SIGN'] = signature
        prepared.headers['FTX-TS'] = str(ts)
        return request, prepared

    # BINANCE SPECIFIC FUNCTION
    def _get_pair_info(self) -> dict:
        """
        Note: This output is used for standardization purpose because binance order api has decimal restriction per
        pair.
        Returns:
            a dict where the key is equal to the pair symbol and the value is a dict that contains
            the following information "quantityPrecision" and "quantityPrecision".
        """
        info = self.client.exchange_info()

        output = {}

        for x in info['symbols']:
            output[x['symbol']] = {}
            output[x['symbol']]['quantityPrecision'] = x['quantityPrecision']
            output[x['symbol']]['pricePrecision'] = x['pricePrecision']

        return output

    # STANDARDIZED FUNCTIONS
    def setup_account(self, base_asset: str, leverage: int, bankroll: float):
        """
        Note: This function is used to setup the parameters of the bot and assert the status

        Args:
            base_asset:
            leverage:
            bankroll:

        Returns:
        """

        accounts = self.client.account(recvWindow=6000)
        positions_info = self.client.get_position_risk(recvWindow=6000)
        position_mode = self.client.get_position_mode(recvWindow=2000)

        for info in positions_info:

            # ISOLATE MARGIN TYPE -> ISOLATED
            if info['marginType'] != 'isolated':
                self.client.change_margin_type(
                    symbol=info['symbol'],
                    marginType="ISOLATED",
                    recvWindow=5000
                )

            # SET LEVERAGE
            if int(info['leverage']) != leverage:
                self.client.change_leverage(
                    symbol=info['symbol'],
                    leverage=leverage,
                    recvWindow=6000
                )

        if position_mode['dualSidePosition']:
            self.client.change_position_mode(
                dualSidePosition="false",
                recvWindow=5000
            )

        for x in accounts["assets"]:

            if x["asset"] == base_asset:
                # Assert_1: The account need to have the minimum bankroll
                assert float(x['availableBalance']) >= bankroll
                # Assert_2: The account has margin available
                assert x['marginAvailable']

            if x['asset'] == "BNB" and float(x["availableBalance"]) == 0:
                print(f"You can save Tx Fees if you transfer BNB in your Future Account")

    def get_server_time(self) -> int:
        response = self.client.time()
        return response['serverTime']

    def get_all_pairs(self) -> list:
        info = self.client.exchange_info()

        list_pairs = []

        for pair in info['symbols']:
            list_pairs.append(pair['symbol'])

        return list_pairs

    def _get_earliest_valid_timestamp(self, symbol: str, interval: str):
        """
        Get the earliest valid open timestamp from Binance
        Args:
            symbol: Name of symbol pair -- BNBBTC
            interval: Binance Kline interval

        :return: first valid timestamp
        """
        kline = self.client.klines(
            symbol=symbol,
            interval=interval,
            limit=1,
            startTime=0,
            endTime=int(time.time() * 1000)
        )
        return kline[0][0]

    def get_historical(self, pair: str, interval: str, start_time: str, end_time: str):
        """
        Args:
            pair:
            interval:
            start_time:
            end_time:

        Returns:
        """

        # init our list
        output_data = []

        # convert interval to useful value in seconds
        timeframe = interval_to_milliseconds(interval)

        # if a start time was passed convert it
        start_ts = convert_ts_str(start_time)

        # establish first available start timestamp
        if start_ts is not None:
            first_valid_ts = self._get_earliest_valid_timestamp(
                symbol=pair,
                interval=interval
            )
            start_ts = max(start_ts, first_valid_ts)

        # if an end time was passed convert it
        end_ts = convert_ts_str(end_time)
        if end_ts and start_ts and end_ts <= start_ts:
            return output_data

        idx = 0
        while True:
            # fetch the klines from start_ts up to max 500 entries or the end_ts if set
            temp_data = self.client.klines(
                symbol=pair,
                interval=interval,
                limit=self.historical_limit,
                startTime=start_ts,
                endTime=end_ts
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

        return output_data

    def get_tickers_price(self):
        return self.client.ticker_price()

    def get_balance(self) -> dict:
        return self.client.balance(recvWindow=6000)

    def get_account(self):
        return self.client.account(recvWindow=6000)

    def get_positions(self):
        return self.client.get_position_risk(recvWindow=6000)

    def get_income_history(self):
        return self.client.get_income_history(recvWindow=6000)

    def open_position_order(self, pair: str, side: str, quantity: float):
        """
        Note -> Each Open Order
        Args:
            pair:
            side:
            quantity:

        Returns:

        """

        _quantity = float(round(quantity, self.pair_info[pair]['quantityPrecision']))

        return self.client.new_order(
            symbol=pair,
            side=side,
            type='MARKET',
            quantity=_quantity,
        )

    def take_profit_order(self, pair: str, side: str, quantity: float, tp_price: float):
        """
        Notes -> When using closing position we don't need to specify the quantity
        Args:
            pair:
            side:
            quantity:
            tp_price:

        Returns:

        """
        _quantity = float(round(quantity, self.pair_info[pair]['quantityPrecision']))
        _price = float(round(tp_price,  self.pair_info[pair]['pricePrecision']))

        return self.client.new_order(
            symbol=pair,
            side=side,
            type='TAKE_PROFIT',
            stopPrice=_price,
            closePosition=True
        )

    def stop_loss_order(self,  pair: str, side: str, quantity: float, sl_price: float):
        _quantity = float(round(quantity, self.pair_info[pair]['quantityPrecision']))
        _price = float(round(sl_price, self.pair_info[pair]['pricePrecision']))

        return self.client.new_order(
            symbol=pair,
            side=side,
            type='STOP_MARKET',
            stopPrice=_price,
            closePosition=True
        )

    def close_position_order(self, pair: str, side: str, quantity: float):
        """
        Note : it's the exact function as open_position_order but it is used to close position

        Args:
            pair:
            side:
            quantity:

        Returns:
        """
        _quantity = float(round(quantity, self.pair_info[pair]['quantityPrecision']))

        return self.client.new_order(
            symbol=pair,
            side=side,
            type='MARKET',
            quantity=_quantity,
        )

    def cancel_order(self, pair: str, order_id: str):
        return self.client.cancel_order(
            symbol=pair,
            orderId=order_id,
            recvWindow=2000
        )

    def cancel_all_orders(self):
        pass

    def close_all_positions(self):
        pass

