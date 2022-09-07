from requests import Request, Session
import hmac
import urllib.parse as parse
import hashlib
import base64
import datetime


class Huobi:

    def __init__(self,
                 key: str,
                 secret: str,
                 testnet: bool):

        self.api_key = key
        self.api_secret = secret

        self.based_endpoint = "https://api.hbdm.com"
        self._session = Session()

    def generate_signature(self, method: str, request_path: str, _params: dict):

        sign_params = _params if _params else {}
        sign_params.update({
            "AccessKeyId": self.api_key,
            "SignatureMethod": "HmacSHA256",
            "SignatureVersion": "2",
            "Timestamp": datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S"),
        })
        sorted_params = sorted(sign_params.items(), key=lambda d: d[0], reverse=False)
        encode_params = parse.urlencode(sorted_params)
        host_url = self.based_endpoint.replace("https://", "")
        payload = [method, host_url, request_path, encode_params]
        payload = "\n".join(payload)
        hash_ = hmac.new(
            self.api_secret.encode(encoding="utf8"),
            payload.encode(encoding="UTF8"),
            digestmod=hashlib.sha256
        )
        signature = base64.b64encode(hash_.digest())
        sign_params['Signature'] = signature.decode()
        return sign_params

    def _send_request(self, end_point: str, request_type: str, params: dict = None, is_signed: bool = False):

        uri = f'{self.based_endpoint}{end_point}'

        if is_signed:
            _signed = self.generate_signature(request_type, end_point, params)
            request = Request(request_type, uri, params=_signed, json=params)
        else:
            request = Request(request_type, uri, json=params)

        prepared = request.prepare()
        prepared.headers['User-Agent'] = "NovaLabs"
        if request_type == "GET":
            prepared.headers['Content-Type'] = "application/x-www-form-urlencoded"
        else:
            prepared.headers["Accept"] = "application/json"
            prepared.headers['Content-Type'] = "application/json"
        response = self._session.send(prepared)
        return response.json()

    def get_contract_info(self):
        return self._send_request(
            end_point="/api/v1/contract_contract_info",
            request_type="GET",
        )

    def get_contract_record(self, pair: str):

        _params = {
            "symbol": pair
        }

        response = self._send_request(
            end_point="/api/v1/contract_financial_record",
            request_type="POST",
            params=_params,
            is_signed=True

        )
        return response
