from binance.um_futures import UMFutures
from decouple import config
from datetime import datetime
from nova.clients.helpers import interval_to_milliseconds, convert_ts_str
import time


class Binance:

    def __init__(self,
                 key: str,
                 secret: str):

        self._client = UMFutures(key=key, secret=secret)
        self.historical_limit = 1000

    # STANDARDIZED FUNCTIONS

    def get_server_time(self) -> int:
        response = self._client.time()
        return response['serverTime']

    def get_all_pairs(self) -> list:
        info = self._client.exchange_info()

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
        kline = self._client.klines(
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
            temp_data = self._client.klines(
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
        return self._client.ticker_price()

    def get_balance(self) -> dict:
        return self._client.balance(recvWindow=6000)

    def get_account(self):
        return self._client.account(recvWindow=6000)

    def change_leverage(self, pair: str, leverage: int):
        return self._client.change_leverage(
            symbol=pair,
            leverage=leverage,
            recvWindow=6000
        )

    def change_position_mode(self, is_dual_side: str) -> dict:
        return self._client.change_position_mode(
            dualSidePosition=is_dual_side,
            recvWindow=5000
        )

    # BINANCE SPECIFIC FUNCTIONS
    def change_margin_type(self, pair: str, margin_type: str):
        return self._client.change_margin_type(
            symbol=pair,
            marginType=margin_type,
            recvWindow=5000
        )

    def get_position_mode(self):
        return self._client.get_position_mode(recvWindow=2000)

    def get_positions(self):
        return self._client.get_position_risk(recvWindow=6000)

    def get_income_history(self):
        return self._client.get_income_history(recvWindow=6000)

    def open_order(self, pair: str, side: str, side_type: str, quantity: float, price: float):
        return self._client.new_order(
            symbol=pair,
            side=side,
            type=side_type,
            quantity=quantity,
        )

    def take_profit_order(self):
        pass

    def stop_loss_order(self):
        pass

    def close_position_order(self):
        pass

    def cancel_order(self):
        pass

    def cancel_all_orders(self):
        pass



