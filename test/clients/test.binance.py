from nova.clients.binance import Binance
from decouple import config

from datetime import datetime

client = Binance(key=config("BinanceAPIKey"), secret=config("BinanceAPISecret"))



