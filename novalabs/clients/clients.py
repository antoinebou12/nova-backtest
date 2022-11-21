from novalabs.clients.binance import Binance
from novalabs.clients.ftx import FTX
from novalabs.clients.coinbase import Coinbase
from novalabs.clients.okx import OKX
from novalabs.clients.kraken import Kraken
from novalabs.clients.kucoin import Kucoin
from novalabs.clients.huobi import Huobi
from novalabs.clients.gemini import Gemini
from novalabs.clients.gate import Gate
from novalabs.clients.cryptocom import Cryptocom
from novalabs.clients.bybit import Bybit
from novalabs.clients.oanda import Oanda


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
    elif exchange == 'oanda':
        return Oanda(key=key, secret=secret, testnet=testnet)


