from nova.api.nova_client import NovaClient
from nova.utils.constant import EXCEPTION_LIST_BINANCE
from decouple import config
from binance.client import Client

nova_client = NovaClient(config('NovaAPISecret'))

# GET BINANCE FUTURE USDT PAIRS

client = Client(
    config("BinanceAPIKey"),
    config("BinanceAPISecret"),
    testnet=False
)

list_pair = []
all_pair = client.futures_symbol_ticker()


for pair in all_pair:
    if 'USDT' in pair['symbol'] and pair['symbol'] not in EXCEPTION_LIST_BINANCE:
        list_pair.append(pair['symbol'])


all_all_pairs = []


for x in list_pair:
    info = client.get_symbol_info(x)
    all_all_pairs.append(info)




