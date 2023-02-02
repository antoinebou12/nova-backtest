from requests import Request, Session
from urllib.parse import urlencode
import numpy as np
import hashlib
import time
import hmac
from typing import Union
import base64
import json


class MEXC:

    def __init__(self,
                 key: str,
                 secret: str,
                 passphrase: str = '',
                 testnet: bool = False
                 ):

        self.api_key = key
        self.api_secret = secret

        self.based_endpoint = "https://contract.mexc.com/"

        self._session = Session()

        self.historical_limit = 1000

        # self.pairs_info = self.get_pairs_info()
        
    # API REQUEST FORMAT
    def _send_request(self, end_point: str, request_type: str, params: dict = {}, signed: bool = False):
                
        if params is None:
            params = {}

        timestamp = str(int(time.time() * 1000))
        params = dict(sorted(params.items()))      
        
        if signed :
            query_string = ""
            
            if params:
                query_string = '?' + urlencode(params, True).replace("%40", "@")
                

            auth = self.api_key + timestamp + query_string
            
            print(auth)
            print(f'{self.based_endpoint}{end_point}{query_string}')
            
            if request_type == 'POST':
                request = Request(request_type, f'{self.based_endpoint}{end_point}{query_string}', data=json.dumps(params))
            else :
                request = Request(request_type, f'{self.based_endpoint}{end_point}{query_string}', data=json.dumps(params))

            mac = hmac.new(self.api_secret.encode('latin-1'),
                           auth.encode('latin-1'),
                           hashlib.sha256)
            
            prepared = request.prepare()
            signature = base64.b16encode(mac.digest()).lower()
            prepared.headers['Signature'] =signature
            prepared.headers['Request-Time'] = timestamp
            prepared.headers['ApiKey'] = self.api_key
            
            print(prepared.headers)
                           
        else :
            request = Request(request_type, f'{self.based_endpoint}{end_point}', data=json.dumps(params))
            prepared = request.prepare()

        prepared.headers['Content-Type'] = "application/json"
        prepared.headers['User-Agent'] = "NovaLabs"
        
        response = self._session.send(prepared)
        
        data = response.json()

        return data
    
    def get_server_time(self) -> int:
        """
        Returns:
            the timestamp in milliseconds
        """
        data = self._send_request(
            end_point=f"api/v1/contract/ping",
            request_type="GET",
            signed=False
        )
        return data['data']
    
    def get_pairs_info(self) -> dict:
        """
        Note: This output is used for standardization purpose because binance order api has
        decimal restriction per pair.
        Returns:
            a dict where the key is equal to the pair symbol and the value is a dict that contains
            the following information "quantityPrecision" and "quantityPrecision".
        """
        info = self._send_request(
            end_point=f"api/v1/contract/detail",
            request_type="GET",
        )['data']
        
        output = {}
        
        for symbol in info:

            pair = symbol['symbol']

            output[pair]={}
            output[pair]['based_asset'] = symbol['baseCoin']
            output[pair]['quote_asset'] = symbol['quoteCoin']

            output[pair]['tick_size'] = float(symbol['priceUnit'])
            price_increment = np.format_float_positional(float(symbol['priceUnit']), trim='-')
            price_precision = int(str(price_increment)[::-1].find('.')) if float(symbol['priceUnit']) < 1 else 1
            output[pair]['pricePrecision'] = price_precision

            size_increment = np.format_float_positional(float(symbol["contractSize"]), trim='-')
            qty_precision = int(str(size_increment)[::-1].find('.')) if float(symbol['contractSize']) < 1 else 1
            output[pair]['step_size'] = float(symbol['contractSize'])
            output[pair]['quantityPrecision'] = qty_precision

            output[pair]['minQuantity'] = float(symbol['minVol'])
            output[pair]['maxQuantity'] = float(symbol['maxVol']) 

        return output

    def get_account_info(self):
        
        return self._send_request(
            end_point=f"api/v1/private/account/assets",
            request_type="GET",
            signed=True
        )

    def _get_candles(self, pair: str, interval: str, start_time: int, end_time: int) -> Union[dict, list]:
        """
        Args:
            pair: pair to get information from
            interval: granularity of the candle ['Min1', 'Min60', 'Hour4', ... 'Day1']
            start_time: timestamp in seconds of the starting date
            end_time: timestamp in seconds of the end date
        Returns:
            the none formatted candle information requested
        """
        _endpoint = f"api/v1/contract/kline/{pair}?interval={interval}&start={start_time}&end={end_time}"

        return self._send_request(
            end_point=_endpoint,
            request_type="GET",
        )['data']
