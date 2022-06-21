from nova.clients.binance import Binance
from decouple import config

client = Binance(key=config("BinanceAPIKey"), secret=config("BinanceAPISecret"))

_pair = "BTCUSDT"
_side = "BUY"
_quantity = 0.000731

response = client.open_position_order(
    pair=_pair,
    side=_side,
    quantity=_quantity
)
