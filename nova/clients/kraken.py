import time
from requests import Request, Session
import hmac
from urllib.parse import urlencode
import hashlib
import base64


class Kraken:

    def __init__(
            self,
            key: str,
            secret: str,
            testnet: bool = False
    ):

        self.api_key = key
        self.api_secret = secret
        self.based_endpoint = "https://futures.kraken.com/derivatives"
        if testnet:
            self.based_endpoint = "https://demo-futures.kraken.com"

        self._session = Session()

        self.historical_limit = 1000

        self.pairs_info = self.get_pairs_info()

    def _send_request(self, end_point: str, request_type: str, signed: bool = False, params: str = ""):
        request = Request(request_type, f'{self.based_endpoint}{end_point}')
        prepared = request.prepare()
        prepared.headers['Content-Type'] = "application/json;charset=utf-8"
        prepared.headers['User-Agent'] = "NovaLabs"

        if signed:
            prepared.headers['apiKey'] = self.api_key

            nonce = str(int(time.time() * 1000))

            concat_str = (params + nonce + end_point).encode()
            sha256_hash = hashlib.sha256(concat_str).digest()

            signature = hmac.new(base64.b64decode(self.api_secret),
                                 sha256_hash,
                                 hashlib.sha512
                                 )

            rebase = base64.b64encode(signature.digest())

            prepared.headers['nonce'] = nonce
            prepared.headers['authent'] = rebase.decode()

        response = self._session.send(prepared)

        return response.json()

    @staticmethod
    def get_server_time() -> int:
        """
        Returns:
            the timestamp in milliseconds
        """
        return int(time.time() * 1000)

    def get_pairs_info(self):
        data = self._send_request(
            end_point=f"/api/v3/instruments",
            request_type="GET",
        )['instruments']

        print(data)
        #
        # output = {}
        #
        # for symbol in data:
        #     if symbol['contractType'] == 'PERPETUAL':
        #         output[symbol['symbol']] = {}
        #
        #         output[symbol['symbol']]['quote_asset'] = symbol['quoteAsset']
        #
        #         for fil in symbol['filters']:
        #             if fil['filterType'] == 'PRICE_FILTER':
        #                 tick_size = str(float(fil['tickSize']))
        #                 output[symbol['symbol']]['pricePrecision'] = min(tick_size[::-1].find('.'),
        #                                                                  symbol['pricePrecision'])
        #             if fil['filterType'] == 'LOT_SIZE':
        #                 step_size = str(float(fil['stepSize']))
        #                 output[symbol['symbol']]['quantityPrecision'] = min(step_size[::-1].find('.'),
        #                                                                     symbol['quantityPrecision'])
        #                 output[symbol['symbol']]['minQuantity'] = float(fil['minQty'])
        #
        #             if fil['filterType'] == 'MARKET_LOT_SIZE':
        #                 output[symbol['symbol']]['maxQuantity'] = float(fil['maxQty'])
        #
        # return output

    def get_instrument(self):
        return self._send_request(
            end_point=f"/api/v3/instruments",
            request_type="GET"
        )

    def get_account(self):
        return self._send_request(
            end_point=f"/api/v3/accounts",
            request_type="GET",
            is_signed=True
        )
