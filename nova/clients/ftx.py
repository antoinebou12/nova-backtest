from requests import Request, Session, Response
import time
import hmac
from decouple import config


class FTX:

    def __init__(self,
                 key: str,
                 secret: str):
        self.api_key = key
        self.api_secret = secret
        self.based_endpoint = "https://ftx.com/api"
        self._session = Session()

    def _create_request(self, end_point: str, request_type: str):
        ts = int(time.time() * 1000)
        request = Request(request_type, f'{self.based_endpoint}{end_point}')
        prepared = request.prepare()
        signature_payload = f'{ts}{prepared.method}{prepared.path_url}'.encode()
        signature = hmac.new(self.api_secret.encode(), signature_payload, 'sha256').hexdigest()
        prepared.headers['FTX-KEY'] = self.api_key
        prepared.headers['FTX-SIGN'] = signature
        prepared.headers['FTX-TS'] = str(ts)

        return request, prepared

    def get_sub_accounts(self):

        _request, _prepared = self._create_request(end_point="/subaccounts", request_type="GET")
        response = self._session.send(_prepared)

        return response.json()

    def get_sub_accounts_balance(self, sub_account_name: str):

        _request, _prepared = self._create_request(
            end_point=f"/subaccounts/{sub_account_name}/balances",
            request_type="GET"
        )

        response = self._session.send(_prepared)
        return response.json()




client = FTX(key=config("ftxAPIkey"), secret=config("ftxAPIsecret"))


sub_accounts = client.get_sub_accounts()

balance = client.get_sub_accounts_balance(sub_account_name="novalabs")
