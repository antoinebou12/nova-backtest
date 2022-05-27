from nova.api.nova_client import NovaClient
from decouple import config
from binance.client import Client


nova_client = NovaClient(config('NovaAPISecret'))


# For testing
def get_binance_pairs():
    binance_client = Client(config("BinanceAPIKey"), config("BinanceAPISecret"))
    all_pair = binance_client.futures_position_information()
    list_pair = []
    for pair in all_pair:
        if 'USDT' in pair['symbol']:
            list_pair.append(pair['symbol'].replace('USDT', '/USDT'))
    return list_pair



nova_client.create_pairs(

)








