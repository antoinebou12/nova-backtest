import time
from requests import Request, Session
import hmac
import urllib.parse as parse
import hashlib
import base64


class Huobi:

    def __init__(self,
                 key: str,
                 secret: str):

        self.api_key = key
        self.api_secret = secret

        self.based_endpoint = "https://futures.kraken.com/derivatives"
        self._session = Session()

    def generate_signature(self, method: str, params, request_path):
        if request_path.startswith("http://") or request_path.startswith("https://"):
            host_url = parse.urlparse(request_path).hostname.lower()
            request_path = '/' + '/'.join(request_path.split('/')[3:])
        else:
            host_url = parse.urlparse(self._host).hostname.lower()
        sorted_params = sorted(params.items(), key=lambda d: d[0], reverse=False)
        encode_params = parse.urlencode(sorted_params)
        payload = [method, host_url, request_path, encode_params]
        payload = "\n".join(payload)
        payload = payload.encode(encoding="UTF8")
        secret_key = self.api_secret.encode(encoding="utf8")
        digest = hmac.new(secret_key, payload, digestmod=hashlib.sha256).digest()
        signature = base64.b64encode(digest)
        signature = signature.decode()
        return signature

    def _send_request(self, end_point: str, request_type: str, is_signed: bool = False, post_data: str = ""):

        request = Request(request_type, f'{self.based_endpoint}{end_point}')

        prepared = request.prepare()
        prepared.headers['Content-Type'] = "application/x-www-form-urlencoded"
        prepared.headers['User-Agent'] = "NovaLabs"
        prepared.body
        if is_signed:
            prepared.headers['apiKey'] = self.api_key
            prepared.headers['authent'], prepared.headers['nonce'] = self._get_signature(post_data, end_point)

        response = self._session.send(prepared)
        return response.json()

    def get_exchange_info(self):
        pass
