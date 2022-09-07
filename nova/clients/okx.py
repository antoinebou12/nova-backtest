from requests import Request, Session
import hmac
import base64
import json
import datetime


class OKX:

    def __init__(self,
                 key: str,
                 secret: str,
                 pass_phrase: str,
                 testnet: bool):
        self.api_key = key
        self.api_secret = secret
        self.pass_phrase = pass_phrase

        self.based_endpoint = "https://www.okx.com"
        self._session = Session()

    def _send_request(self, end_point: str, request_type: str, params: dict = None):

        now = datetime.datetime.utcnow()
        timestamp = now.isoformat("T", "milliseconds") + "Z"

        body = json.dumps(params) if request_type == "POST" else ""

        to_hash = str(timestamp) + str.upper(request_type) + end_point + body

        mac = hmac.new(bytes(self.api_secret, encoding='utf8'),
                       bytes(to_hash, encoding='utf-8'),
                       digestmod='sha256')

        d = mac.digest()

        signature = base64.b64encode(d)

        request = Request(request_type, f'{self.based_endpoint}{end_point}')
        prepared = request.prepare()

        prepared.headers['Content-Type'] = "application/json"
        prepared.headers['OK-ACCESS-KEY'] = self.api_key
        prepared.headers['OK-ACCESS-SIGN'] = signature
        prepared.headers['OK-ACCESS-PASSPHRASE'] = self.pass_phrase
        prepared.headers['OK-ACCESS-TIMESTAMP'] = timestamp

        if body:
            prepared.body = body

        response = self._session.send(prepared)

        return response.json()

    def get_status(self):
        return self._send_request(
            end_point=f"/api/v5/system/status",
            request_type="GET"
        )

    def get_balances(self):

        return self._send_request(
            end_point=f"/api/v5/account/balance",
            request_type="GET"
        )

    def get_positions(self):

        return self._send_request(
            end_point=f"/api/v5/account/positions",
            request_type="GET"
        )





