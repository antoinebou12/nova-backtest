from requests import Request, Session
import json
from nova.utils.helpers import interval_to_oanda_granularity


class Oanda:

    def __init__(self,
                 key: str = "",
                 secret: str = "",
                 testnet: bool = False
                 ):

        self.api_key = key
        self.api_secret = secret
        self.based_endpoint = "	https://api-fxpractice.oanda.com" if testnet else "https://api-fxtrade.oanda.com"
        self._session = Session()
        self.historical_limit = 1500

        self.pairs_info = self.get_pairs_info()

    def _send_request(self, end_point: str, request_type: str, params: dict = None, signed: bool = False):
        url = f'{self.based_endpoint}{end_point}'
        request = Request(request_type, url, data=json.dumps(params))
        prepared = request.prepare()
        prepared.headers['Content-Type'] = 'application/json'
        prepared.headers['OANDA-Agent'] = 'NovaLabs'
        prepared.headers['Authorization'] = f'Bearer {self.api_secret}'
        prepared.headers['Accept-Datetime-Format'] = 'UNIX'

        response = self._session.send(prepared)
        return response.json()

    def get_pairs_info(self):
        response = self._send_request(
            end_point=f"/v3/accounts/{self.api_key}/instruments",
            params={"accountID": self.api_key},
            request_type="GET"
        )['instruments']

        pairs_info = {}

        for pair in response:

            if pair['type'] == 'CURRENCY':

                _name = pair['name']

                pairs_info[_name] = {}

                pairs_info[_name]['maxQuantity'] = float(pair['maximumOrderUnits'])
                pairs_info[_name]['minQuantity'] = float(pair['minimumTradeSize'])

                pairs_info[_name]['pricePrecision'] = int(pair['displayPrecision'])
                pairs_info[_name]['quantityPrecision'] = 1

        return pairs_info

    def _get_candles(self, pair: str, interval: str, start_time: int, end_time: int):
        """
        Args:
            pair: pair to get information from
            interval: granularity of the candle ['1m', '1h', ... '1d']
            start_time: timestamp in milliseconds of the starting date
            end_time: timestamp in milliseconds of the end date
        Returns:
            the none formatted candle information requested
        """

        gran = interval_to_oanda_granularity(interval=interval)

        _start = start_time/1000
        _end = end_time/1000
        _args = f"?price=M&granularity={gran}&from={_start}&to={_end}"

        return self._send_request(
            end_point=f"/v3/instruments/{pair}/candles{_args}",
            params={
                "price": "M",
                "granularity": gran,
                "from": str(_start),
                "to": str(_end)
            },
            request_type="GET"
        )



from decouple import config

client = Oanda(
    key=config(f"oandaTestAPIKey"),
    secret=config(f"oandaTestAPISecret"),
    testnet=True
)

data = client._get_candles(
        pair='EUR_USD',
        interval='15m',
        start_time=1666268570000,
        end_time=1668132570000
)


