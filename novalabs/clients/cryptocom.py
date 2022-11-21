from requests import Request, Session
import hmac
import base64
import json
import time
import hashlib


class Cryptocom:

    def __init__(self,
                 key: str,
                 secret: str,
                 testnet: bool
                 ):
        self.api_key = key
        self.api_secret = secret

        self.based_endpoint = "https://api.crypto.com/v2"
        self._session = Session()

    def _send_request(self, end_point: str, request_type: str, params: dict = None):

        request = Request(request_type, f'{self.based_endpoint}{end_point}', data=params)
        prepared = request.prepare()

        prepared.headers['Content-Type'] = "application/json"
        prepared.headers['Accept'] = "application/json"

        request_content = ""
        if params:
            request_content = json.dumps(params)

        t = time.time()
        m = hashlib.sha512()
        m.update((request_content or "").encode('utf-8'))

        hashed_payload = m.hexdigest()
        s = '%s\n%s\n%s\n%s\n%s' % (request_type, end_point, request_content or "", hashed_payload, t)
        signature = hmac.new(self.api_secret.encode('utf-8'), s.encode('utf-8'), hashlib.sha512).hexdigest()

        prepared.headers['KEY'] = "application/json"
        prepared.headers['Timestamp'] = str(t)
        prepared.headers['SIGN'] = signature

        response = self._session.send(prepared)

        return response.json()
