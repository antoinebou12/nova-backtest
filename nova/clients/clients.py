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
from nova.clients.bybit import Bybit


def clients(
        exchange: str,
        key: str = "",
        secret: str = "",
        passphrase: str = "",
        testnet: bool = False
):

    if exchange == 'binance':
        return Binance(key=key, secret=secret, testnet=testnet)
    elif exchange == 'ftx':
        return FTX(key=key, secret=secret, testnet=testnet)
    elif exchange == 'coinbase':
        return Coinbase(key=key, secret=secret, pass_phrase=passphrase, testnet=testnet)
    elif exchange == 'okx':
        return OKX(key=key, secret=secret, pass_phrase=passphrase, testnet=testnet)
    elif exchange == 'kraken':
        return Kraken(key=key, secret=secret, testnet=testnet)
    elif exchange == 'kucoin':
        return Kucoin(key=key, secret=secret, pass_phrase=passphrase, testnet=testnet)
    elif exchange == 'huobi':
        return Huobi(key=key, secret=secret, testnet=testnet)
    elif exchange == 'gemini':
        return Gemini(key=key, secret=secret, testnet=testnet)
    elif exchange == 'gate':
        return Gate(key=key, secret=secret, testnet=testnet)
    elif exchange == 'gate':
        return Cryptocom(key=key, secret=secret, testnet=testnet)
    elif exchange == 'bybit':
        return Bybit(key=key, secret=secret, testnet=testnet)


