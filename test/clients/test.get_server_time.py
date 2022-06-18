from nova.clients.binance import Binance
from nova.clients.ftx import FTX

from decouple import config
import time


def test_get_server_time(exchange: str):
    if exchange == 'binance':
        client = Binance(key=config("BinanceAPIKey"), secret=config("BinanceAPISecret"))
    elif exchange == 'ftx':
        client = FTX(key=config("ftxAPIkey"), secret=config("ftxAPIsecret"))
    server_time = client.get_server_time()
    min_dif = (time.time() - 1) * 1000
    max_dif = (time.time() + 1) * 1000
    assert type(server_time) == int
    assert (server_time > min_dif) and (server_time < max_dif)


test_get_server_time('binance')
test_get_server_time('ftx')



