from requests import Request, Session
import hmac
import base64
import json
import time
import hashlib
import datetime


class Gemini:

    def __init__(self,
                 key: str,
                 secret: str,
                 testnet: bool
                 ):
        self.api_key = key
        self.api_secret = secret

        self.based_endpoint = "https://api.gemini.com/v1"
        self._session = Session()

    def _send_request(self, end_point: str, request_type: str, params: dict = None):

        request = Request(request_type, f'{self.based_endpoint}{end_point}', data=params)
        prepared = request.prepare()

        payload_nonce = time.time()

        payload = {"request": end_point, "nonce": payload_nonce}

        encoded_payload = json.dumps(payload)
        b64 = base64.b64encode(encoded_payload.encode())
        signature = hmac.new(self.api_secret.encode(), b64, hashlib.sha384).hexdigest()

        prepared.headers['Content-Type'] = "text/plain"
        prepared.headers['X-GEMINI-APIKEY'] = self.api_key
        prepared.headers['X-GEMINI-PAYLOAD'] = encoded_payload
        prepared.headers['X-GEMINI-SIGNATURE'] = signature
        prepared.headers['Cache-Control'] = "no-cache"

        response = self._session.send(prepared)

        return response.json()

    def get_pairs(self):
        return self._send_request(
            end_point=f"/symbols",
            request_type="GET",
        )

    def get_balance(self):
        return self._send_request(
            end_point=f"/balances",
            request_type="POST",
        )