import pandas as pd
from requests import Request, Session
import time
import hmac
from decouple import config
import re
from datetime import datetime
import calendar


class FTX:

    def __init__(self,
                 key: str,
                 secret: str):
        self.api_key = key
        self.api_secret = secret
        self.based_endpoint = "https://ftx.com/api"
        self._session = Session()
        self.historical_limit = 1500

    def _create_request(self, end_point: str, request_type: str, **kwargs):
        ts = int(time.time() * 1000)
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

    # STANDARDIZED FUNCTIONS
    @staticmethod
    def get_server_time() -> int:
        return int(time.time() * 1000)

    def get_all_pairs(self):
        _request, _prepared = self._create_request(
            end_point=f"/futures",
            request_type="GET"
        )
        response = self._session.send(_prepared)
        data = response.json()

        list_pairs = []
        for pair in data['result']:
            list_pairs.append(pair['name'])
        return list_pairs

    def _get_earliest_valid_timestamp(self, pair: str):
        """
        Get the earliest valid open timestamp from Binance
        Args:
            symbol: Name of symbol pair -- BNBBTC
            interval: Binance Kline interval

        :return: first valid timestamp
        """

        request_name = f"/markets/{pair}/candles?resolution=172800&start_time={0}&end_time={int(time.time())}"

        _request, _prepared = self._create_request(
            end_point=f"{request_name}",
            request_type="GET"
        )

        response = self._session.send(_prepared)
        data = response.json()
        return int(data['result'][0]['time'] / 1000)

    @staticmethod
    def _get_interval_time(interval: str):
        """
        Notes: FTX platform can only

        Args:
            interval:

        Returns:
        """

        assert interval in ['1m', '5m', '15m', '1h', '4h', '1d']

        multi = int(float(re.findall(r'\d+', interval)[0]))

        if "m" in interval:
            return multi * 60
        elif "h" in interval:
            return multi * 3600
        elif "d":
            return multi * 86400

    @staticmethod
    def _get_timestamp_time(str_time: str):
        date = datetime.strptime(str_time, "%d %b, %Y")

        trans = date.timetuple()
        return int(calendar.timegm(trans))

    def get_historical(self, pair: str, interval: str, start_time: str, end_time: str):
        """

        Args:
            pair:
            interval:
            start_time:
            end_time:

        Returns:

        """
        output_data = []

        interval_time = self._get_interval_time(interval=interval)
        start = self._get_timestamp_time(str_time=start_time)
        end = self._get_timestamp_time(str_time=end_time)

        first_valid_ts = self._get_earliest_valid_timestamp(
            pair=pair
        )

        start_ts = max(start, first_valid_ts)

        idx = 0

        while True:

            end_ts = start_ts + interval_time * self.historical_limit
            end_t = min(end_ts, end)

            request_name = f"/markets/{pair}/candles?resolution={interval_time}&start_time={start_ts}&end_time={end_t}"

            _request, _prepared = self._create_request(
                end_point=f"{request_name}",
                request_type="GET"
            )

            response = self._session.send(_prepared)

            data = response.json()

            # append this loops data to our output data
            if data['result']:
                output_data += data['result']

            # increment next call by our timeframe
            start_ts = int(data['result'][-1]['time']/1000) + interval_time

            # exit loop if we reached end_ts before reaching <limit> klines
            if end_ts and start_ts >= end:
                break

            # sleep after every 3rd call to be kind to the API
            idx += 1
            if idx % 3 == 0:
                time.sleep(1)

        return output_data

    def get_sub_accounts(self):
        _request, _prepared = self._create_request(end_point="/subaccounts", request_type="GET")
        response = self._session.send(_prepared)
        return response.json()

    def get_sub_accounts_balance(self, sub_account_name: str):
        _request, _prepared = self._create_request(
            end_point=f"/subaccounts/{sub_account_name}/balances",
            request_type="GET"
        )
        response = self._session.send(_prepared)
        return response.json()

    def get_account(self):
        _request, _prepared = self._create_request(
            end_point=f"/account",
            request_type="GET"
        )
        response = self._session.send(_prepared)
        return response.json()

    def get_positions(self):
        _request, _prepared = self._create_request(
            end_point=f"/positions",
            request_type="GET"
        )
        response = self._session.send(_prepared)
        return response.json()

    def change_leverage(self, leverage: int):

        _request, _prepared = self._create_request(
            end_point=f"/account/leverage",
            request_type="POST",
            json={"leverage": leverage}
        )

        response = self._session.send(_prepared)
        return response.json()

    def get_opened_orders_pair(self, pair: str):

        _request, _prepared = self._create_request(
            end_point=f"/orders?market={pair}",
            request_type="GET",
        )

        response = self._session.send(_prepared)
        return response.json()

    def open_order(self, pair: str, side: str, side_type: str, quantity: float, price: float):

        _params = {
            "market": pair,
            "side": side,
            "price": price,
            "type": side_type,
            "size": quantity,
            "reduceOnly": False,
            "ioc": False,
            "postOnly": False,
            "clientId": None
        }

        _request, _prepared = self._create_request(
            end_point=f"/orders",
            request_type="POST",
            json=_params
        )

        response = self._session.send(_prepared)

        return response.json()

    def take_profit_order(self, pair: str, side: str, quantity: float, price: float):

        _params = {
            "market": pair,
            "side": side,
            "triggerPrice": price,
            "size": quantity,
            "type": "takeProfit",
            "reduceOnly": False,
        }
        _request, _prepared = self._create_request(
            end_point=f"/conditional_orders",
            request_type="POST",
            json=_params
        )

        response = self._session.send(_prepared)

        return response.json()

    def stop_loss_order(self, pair: str, side: str, quantity: float, price: float):

        _params = {
            "market": pair,
            "side": side,
            "triggerPrice": price,
            "size": quantity,
            "type": "stop",
            "reduceOnly": False,
        }
        _request, _prepared = self._create_request(
            end_point=f"/orders",
            request_type="POST",
            json=_params
        )

        response = self._session.send(_prepared)

        return response.json()

    def close_position_order(self):
        pass

    def cancel_order(self, order_id: str):

        _request, _prepared = self._create_request(
            end_point=f"/orders/{order_id}",
            request_type="DELETE",
        )

        response = self._session.send(_prepared)

        return response.json

    def cancel_all_orders(self, pair: str):
        _request, _prepared = self._create_request(
            end_point=f"/orders",
            request_type="DELETE",
            json={"market": pair}
        )

        response = self._session.send(_prepared)

        return response.json
        pass








