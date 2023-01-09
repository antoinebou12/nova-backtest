from nova.clients.binance import Binance
from nova.clients.coinbase import Coinbase
from nova.clients.okx import OKX
from nova.clients.kraken import Kraken
from nova.clients.kucoin import Kucoin
from nova.clients.huobi import Huobi
from nova.clients.gate import Gate
from nova.clients.bybit import Bybit
from nova.clients.oanda import Oanda
from nova.clients.mexc import MEXC
from nova.clients.btcex import BTCEX


def clients(
        exchange: str,
        key: str = "",
        secret: str = "",
        passphrase: str = "",
        testnet: bool = False
):

    if exchange == 'binance':
        return Binance(key=key, secret=secret, testnet=testnet)
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
    elif exchange == 'gate':
        return Gate(key=key, secret=secret, testnet=testnet)
    elif exchange == 'bybit':
        return Bybit(key=key, secret=secret, testnet=testnet)
    elif exchange == 'oanda':
        return Oanda(key=key, secret=secret, testnet=testnet)
    elif exchange == 'mexc':
        return MEXC(key=key, secret=secret, testnet=testnet)
    elif exchange == 'btcex':
        return BTCEX(key=key, secret=secret, testnet=testnet)

