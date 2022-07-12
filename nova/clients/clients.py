from nova.clients.binance import Binance
from nova.clients.ftx import FTX
from nova.clients.coinbase import Coinbase
from nova.clients.okx import OKX
from nova.clients.kraken import Kraken
from nova.clients.kucoin import Kucoin
from nova.clients.huobi import Huobi
from nova.clients.gemini import Gemini
from nova.clients.gate import Gate
from nova.clients.cryptocom import Cryptocom


def clients(
        exchange: str,
        key: str,
        secret: str,
        passphrase: str = ""):

    if exchange == 'binance':
        return Binance(key=key, secret=secret)
    elif exchange == 'ftx':
        return FTX(key=key, secret=secret)
    elif exchange == 'coinbase':
        return Coinbase(key=key, secret=secret, pass_phrase=passphrase)
    elif exchange == 'okx':
        return OKX(key=key, secret=secret, pass_phrase=passphrase)
    elif exchange == 'kraken':
        return Kraken(key=key, secret=secret)
    elif exchange == 'kucoin':
        return Kucoin(key=key, secret=secret, pass_phrase=passphrase)
    elif exchange == 'huobi':
        return Huobi(key=key, secret=secret)
    elif exchange == 'gemini':
        return Gemini(key=key, secret=secret)
    elif exchange == 'gate':
        return Gate(key=key, secret=secret)
    elif exchange == 'gate':
        return Cryptocom(key=key, secret=secret)
