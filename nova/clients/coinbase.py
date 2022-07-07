from requests import Request, Session
import hmac
import base64
import json
import time
import hashlib


class Coinbase:

    def __init__(self,
                 key: str,
                 secret: str,
                 pass_phrase: str):
        self.api_key = key
        self.api_secret = secret
        self.pass_phrase = pass_phrase

        self.based_endpoint = "https://api.pro.coinbase.com"
        self._session = Session()

    def _send_request(self, end_point: str, request_type: str, params: dict = None, signed: bool = False):

        timestamp = str(time.time())
        body = ""

        if params:
            body = json.dumps(params)

        request = Request(request_type, f'{self.based_endpoint}{end_point}')
        prepared = request.prepare()

        prepared.headers['Content-Type'] = "application/json"

        if signed:
            message = ''.join([timestamp, request_type, end_point, body])
            message = message.encode('ascii')
            hmac_key = base64.b64decode(self.api_secret)
            signature = hmac.new(hmac_key, message, hashlib.sha256)
            signature_b64 = base64.b64encode(signature.digest()).decode('utf-8')

            prepared.headers['CB-ACCESS-KEY'] = self.api_key
            prepared.headers['CB-ACCESS-SIGN'] = signature_b64
            prepared.headers['CB-ACCESS-PASSPHRASE'] = self.pass_phrase
            prepared.headers['CB-ACCESS-TIMESTAMP'] = timestamp

        if body:
            prepared.body = body

        response = self._session.send(prepared)

        return response.json()

    def get_account(self):
        return self._send_request(
            end_point=f"/accounts",
            request_type="GET",
            signed=True
        )

    def get_pairs(self):
        return self._send_request(
            end_point=f"/products",
            request_type="GET"
        )

    def convert_currency(self):
        return self._send_request(
            end_point=f"/conversions/conversion_id",
            request_type="GET",
            params={}
        )
