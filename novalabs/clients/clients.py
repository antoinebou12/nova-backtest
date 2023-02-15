from novalabs.clients.binance import Binance
from novalabs.clients.okx import OKX
from novalabs.clients.kucoin import Kucoin
from novalabs.clients.huobi import Huobi
from novalabs.clients.bybit import Bybit
from novalabs.clients.oanda import Oanda
from novalabs.clients.mexc import MEXC
from novalabs.clients.btcex import BTCEX


def clients(
        exchange: str,
        key: str = "",
        secret: str = "",
        passphrase: str = "",
        testnet: bool = False
):

    if exchange == 'binance':
        return Binance(key=key, secret=secret, testnet=testnet)
    elif exchange == 'okx':
        return OKX(key=key, secret=secret, pass_phrase=passphrase, testnet=testnet)
    elif exchange == 'kucoin':
        return Kucoin(key=key, secret=secret, pass_phrase=passphrase, testnet=testnet)
    elif exchange == 'huobi':
        return Huobi(key=key, secret=secret, testnet=testnet)
    elif exchange == 'bybit':
        return Bybit(key=key, secret=secret, testnet=testnet)
    elif exchange == 'oanda':
        return Oanda(key=key, secret=secret, testnet=testnet)
    elif exchange == 'mexc':
        return MEXC(key=key, secret=secret, testnet=testnet)
    elif exchange == 'btcex':
        return BTCEX(key=key, secret=secret, testnet=testnet)

