from nova.clients.helpers import interval_to_milliseconds, convert_ts_str
import time
from requests import Request, Session
import hmac
from urllib.parse import urlencode
import hashlib


class Binance:

    def __init__(self,
                 key: str,
                 secret: str):

        self.api_key = key
        self.api_secret = secret

        self.based_endpoint = "https://fapi.binance.com"
        self._session = Session()

        self.historical_limit = 1000
        self.pair_info = self._get_pair_info()

    # API REQUEST FORMAT
    def _add_signature(self, payload: dict):
        payload['timestamp'] = int(time.time() * 1000)
        query_string = urlencode(payload, True).replace("%40", "@")
        m = hmac.new(self.api_secret.encode("utf-8"), query_string.encode("utf-8"), hashlib.sha256)
        payload['signature'] = m.hexdigest()
        return payload

    def _send_request(self, end_point: str, request_type: str, **kwargs):
        request = Request(request_type, f'{self.based_endpoint}{end_point}', **kwargs)
        prepared = request.prepare()
        prepared.headers['Content-Type'] = "application/json;charset=utf-8"
        prepared.headers['User-Agent'] = "NovaLabs"
        prepared.headers['X-MBX-APIKEY'] = self.api_key
        response = self._session.send(prepared)
        return response.json()

    # BINANCE SPECIFIC FUNCTION
    def change_position_mode(self, dual_position: str):
        _params = self._add_signature(payload={"dualSidePosition": dual_position})
        response = self._send_request(
            end_point=f"/fapi/v1/positionSide/dual",
            request_type="POST",
            params=urlencode(_params, True).replace("%40", "@")
        )
        print(response['msg'])

    def get_position_mode(self):
        _params = self._add_signature(payload={})
        return self._send_request(
            end_point=f"/fapi/v1/positionSide/dual",
            request_type="GET",
            params=urlencode(_params, True).replace("%40", "@")
        )

    def change_margin_type(self, pair: str, margin_type: str):
        _params = self._add_signature(payload={"symbol": pair, "marginType": margin_type})
        response = self._send_request(
            end_point=f"/fapi/v1/marginType",
            request_type="POST",
            params=urlencode(_params, True).replace("%40", "@")
        )
        print(f"{response['msg']}")

    def _get_pair_info(self) -> dict:
        """
        Note: This output is used for standardization purpose because binance order api has decimal restriction per
        pair.
        Returns:
            a dict where the key is equal to the pair symbol and the value is a dict that contains
            the following information "quantityPrecision" and "quantityPrecision".
        """
        info = self.get_exchange_info()

        output = {}

        for x in info['symbols']:
            output[x['symbol']] = {}
            output[x['symbol']]['quantityPrecision'] = x['quantityPrecision']
            output[x['symbol']]['pricePrecision'] = x['pricePrecision']

        return output

    # STANDARDIZED FUNCTIONS
    def change_leverage(self, pair: str, leverage: int):
        _params = self._add_signature(payload={"symbol": pair, "leverage": leverage})
        data = self._send_request(
            end_point=f"/fapi/v1/leverage",
            request_type="POST",
            params=urlencode(_params, True).replace("%40", "@")
        )
        print(f"{pair} leverage is now set to : x{data['leverage']} with max notional to {data['maxNotionalValue']}")

    def get_exchange_info(self):
        return self._send_request(
            end_point=f"/fapi/v1/exchangeInfo",
            request_type="GET",
        )

    def get_position_info(self):
        _params = self._add_signature(payload={})
        return self._send_request(
            end_point=f"/fapi/v2/positionRisk",
            request_type="GET",
            params=urlencode(_params, True).replace("%40", "@")
        )

    def get_account_info(self):
        _params = self._add_signature(payload={})
        return self._send_request(
            end_point=f"/fapi/v2/account",
            request_type="GET",
            params=urlencode(_params, True).replace("%40", "@")
        )

    def setup_account(self, base_asset: str, leverage: int, bankroll: float):
        accounts = self.get_account_info()
        positions_info = self.get_position_info()
        position_mode = self.get_position_mode()

        for info in positions_info:

            # ISOLATE MARGIN TYPE -> ISOLATED
            if info['marginType'] != 'isolated':
                self.change_margin_type(
                    pair=info['symbol'],
                    margin_type="ISOLATED",
                )

            # SET LEVERAGE
            if int(info['leverage']) != leverage:
                self.client.change_leverage(
                    symbol=info['symbol'],
                    leverage=leverage,
                    recvWindow=6000
                )

        if position_mode['dualSidePosition']:
            self.change_position_mode(
                dual_position="false",
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
        return self._send_request(
            end_point=f"/fapi/v1/time",
            request_type="GET"
        )

    def get_all_pairs(self) -> list:
        info = self.get_exchange_info()
        list_pairs = []
        for pair in info['symbols']:
            list_pairs.append(pair['symbol'])
        return list_pairs

    def get_candles(self, pair: str, interval: str, start_time: int, end_time: int, limit: int = None):

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
            params=urlencode(_params, True).replace("%40", "@")
        )

    def _get_earliest_valid_timestamp(self, pair: str, interval: str):
        """
        Get the earliest valid open timestamp from Binance
        Args:
            symbol: Name of symbol pair -- BNBBTC
            interval: Binance Kline interval

        :return: first valid timestamp
        """
        kline = self.get_candles(
            pair=pair,
            interval=interval,
            start_time=0,
            end_time=int(time.time() * 1000),
            limit=1
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
                pair=pair,
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
            temp_data = self.get_candles(
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

        return output_data

    def get_tickers_price(self, pair: str):
        _params = {"symbol": pair}
        return self._send_request(
            end_point=f"/fapi/v1/ticker/price",
            request_type="GET",
            params=urlencode(_params, True).replace("%40", "@")
        )

    def get_balance(self) -> dict:
        _params = self._add_signature(payload={})
        return self._send_request(
            end_point=f"/fapi/v2/balance",
            request_type="GET",
            params=urlencode(_params, True).replace("%40", "@")
        )

    def open_close_order(self, pair: str, side: str, quantity: float):
        _params = self._add_signature(
            payload={
                "symbol": pair,
                "side": side,
                "quantity": float(round(quantity, self.pair_info[pair]['quantityPrecision'])),
                "type": "MARKET"
            }
        )

        return self._send_request(
            end_point=f"/fapi/v1/order",
            request_type="POST",
            params=urlencode(_params, True).replace("%40", "@")
        )

    def take_profit_order(self, pair: str, side: str, quantity: float, tp_price: float):

        _quantity = float(round(quantity, self.pair_info[pair]['quantityPrecision']))
        _params = self._add_signature(
            payload={
                "symbol": pair,
                "side": side,
                "type": "TAKE_PROFIT",
                "stopPrice": float(round(tp_price,  self.pair_info[pair]['pricePrecision'])),
                "quantity ": True
            }
        )

        return self._send_request(
            end_point=f"/fapi/v1/order",
            request_type="POST",
            params=urlencode(_params, True).replace("%40", "@")
        )

    def stop_loss_order(self,  pair: str, side: str, quantity: float, sl_price: float):

        _quantity = float(round(quantity, self.pair_info[pair]['quantityPrecision']))
        _params = self._add_signature(
            payload={
                "symbol": pair,
                "side": side,
                "type": "STOP_MARKET",
                "stopPrice": float(round(sl_price,  self.pair_info[pair]['pricePrecision'])),
                "closePosition": True
            }
        )

        return self._send_request(
            end_point=f"/fapi/v1/order",
            request_type="POST",
            params=urlencode(_params, True).replace("%40", "@")
        )

    def cancel_order(self, pair: str, order_id: str):
        _params = self._add_signature(
            payload={
                "symbol": pair,
                "orderId": order_id,
            }
        )

        return self._send_request(
            end_point=f"/fapi/v1/order",
            request_type="DELETE",
            params=urlencode(_params, True).replace("%40", "@")
        )

    def cancel_pair_orders(self, pair: str):
        _params = self._add_signature(
            payload={
                "symbol": pair,
            }
        )

        return self._send_request(
            end_point=f"/fapi/v1/order",
            request_type="DELETE",
            params=urlencode(_params, True).replace("%40", "@")
        )
