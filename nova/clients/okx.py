from requests import Request, Session
import hmac
import urllib.parse as parse
import hashlib
import base64
import datetime


class OKX:

    def __init__(self,
                 key: str,
                 secret: str,
                 pass_phrase: str):
        self.api_key = key
        self.api_secret = secret
        self.pass_phrase = pass_phrase

        self.based_endpoint = "https://www.okx.com/"
        self._session = Session()

    def _send_request(self, end_point: str, request_type: str, params: dict = None):

        request = Request(request_type, f'{self.based_endpoint}{end_point}')
        prepared = request.prepare()
        prepared.headers['Content-Type'] = "application/json;charset=utf-8"
        prepared.headers['User-Agent'] = "NovaLabs"
        response = self._session.send(prepared)

        return response.json()

    def get_ticker(self, type: str):

        _params = {
            "instType": type
        }





