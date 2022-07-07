from requests import Request, Session
import hmac
import base64
import json
import time
import hashlib


class Kucoin:

    def __init__(self,
                 key: str,
                 secret: str,
                 pass_phrase: str):
        self.api_key = key
        self.api_secret = secret
        self.pass_phrase = pass_phrase

        self.based_endpoint = "https://api-futures.kucoin.com"
        self._session = Session()

    def _send_request(self, end_point: str, request_type: str, params: dict = None, signed: bool = False):

        request = Request(request_type, f'{self.based_endpoint}{end_point}', data=params)
        prepared = request.prepare()

        prepared.headers['Content-Type'] = "application/json"
        prepared.headers['KC-API-KEY-VERSION '] = "2"
        prepared.headers['User-Agent'] = "NovaLabs"
        prepared.headers['Accept'] = "application/json"
        prepared.headers['KC-API-KEY'] = self.api_key
        prepared.headers['KC-API-PASSPHRASE'] = self.pass_phrase

        if signed:
            timestamp = int(time.time() * 1000)
            final_dict = ""
            if params:
                final_dict = json.dumps(params, separators=(',', ':'), ensure_ascii=False)
            sig_str = f"{timestamp}{request_type}{end_point}{final_dict}".encode('utf-8')
            print(sig_str)
            m = hmac.new(self.api_secret.encode('utf-8'), sig_str, hashlib.sha256)
            signature = base64.b64encode(m.digest())

            prepared.headers['KC-API-TIMESTAMP'] = str(timestamp)
            prepared.headers['KC-API-SIGN'] = signature

        response = self._session.send(prepared)

        return response.json()

    def get_account(self):
        return self._send_request(
            end_point=f"/api/v1/account-overview",
            request_type="GET",
            signed=True
        )

    def get_pairs(self):
        return self._send_request(
            end_point=f"/api/v1/contracts/active",
            request_type="GET",
            signed=False
        )


