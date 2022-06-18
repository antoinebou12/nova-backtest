from nova.clients.binance import Binance
from nova.clients.ftx import FTX
from decouple import config


def test_all_pairs(exchange: str):
    if exchange == 'binance':
        client = Binance(key=config("BinanceAPIKey"), secret=config("BinanceAPISecret"))
    elif exchange == 'ftx':
        client = FTX(key=config("ftxAPIkey"), secret=config("ftxAPIsecret"))

    all_pairs = client.get_all_pairs()

    unique_list = list(dict.fromkeys(all_pairs))

    assert all_pairs == unique_list
    assert type(all_pairs) == list

    return all_pairs


data = test_all_pairs('binance')


test_all_pairs('ftx')

perp = []

for x in data:
    if 'USDT' in x:
        perp.append(x)




