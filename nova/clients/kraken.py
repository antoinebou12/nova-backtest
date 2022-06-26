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
            secret: str
    ):

        self.api_key = key
        self.api_secret = secret

        self.based_endpoint = "https://futures.kraken.com/derivatives"
        self._session = Session()

        self.historical_limit = 1000

    def _get_signature(self, post_data: str, end_point: str):
        nonce = str(int(time.time() * 1000))
        concat_str = (post_data + nonce + end_point).encode()
        sha256_hash = hashlib.sha256(concat_str).digest()

        signature = hmac.new(base64.b64decode(self.api_secret),
                             sha256_hash,
                             hashlib.sha512
                             )

        rebase = base64.b64encode(signature.digest())

        return rebase.decode(), nonce

    def _send_request(self, end_point: str, request_type: str, is_signed: bool = False, post_data: str = ""):
        request = Request(request_type, f'{self.based_endpoint}{end_point}')
        prepared = request.prepare()
        prepared.headers['Content-Type'] = "application/json;charset=utf-8"
        prepared.headers['User-Agent'] = "NovaLabs"
        if is_signed:
            prepared.headers['apiKey'] = self.api_key
            prepared.headers['authent'], prepared.headers['nonce'] = self._get_signature(post_data, end_point)

        response = self._session.send(prepared)
        return response.json()

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
