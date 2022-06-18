EXCEPTION_LIST_BINANCE = [
    'BTCSTUSDT', 'BTCDOMUSDT', '1000XECUSDT', 'ETHUSDT_220325',
    '1000BTTCUSDT', '1000SHIBUSDT', 'DEFIUSDT', 'BTCUSDT_220325',
    'API3USDT', 'ANCUSDT', 'IMXUSDT', 'FLOWUSDT', 'TLMUSDT', 'ICPUSDT', 'DODOUSDT', 'AKROUSDT'
]

VAR_NEEDED_FOR_POSITION = [
    'all_entry_time', 'all_entry_point', 'all_entry_price',
    'all_exit_time', 'all_exit_point', 'all_tp', 'all_sl'
]

POSITION_PROD_COLUMNS = [
    'id', 'pair', 'status', 'quantity', 'type', 'side', 'tp_id', 'tp_side',
    'tp_type', 'tp_stopPrice', 'sl_id', 'sl_side', 'sl_type', 'sl_stopPrice',
    'nova_id', 'time_entry'
]


BINANCE_KLINES_COLUMNS = [
    'open_time', 'open', 'high', 'low', 'close', 'volume', 'close_time',
    'quote_asset_volume', 'nb_of_trades', 'taker_base_volume',
    'taker_quote_volume', 'ignore'
]

DATA_FORMATING = {
    "binance": {
        "columns": [
            'open_time', 'open', 'high', 'low', 'close', 'volume', 'close_time',
            'quote_asset_volume', 'nb_of_trades', 'taker_base_volume',
            'taker_quote_volume', 'ignore'
        ],
        "num_var": [
            "open", "high", "low", "close", "volume", "quote_asset_volume",
            "nb_of_trades", "taker_base_volume", "taker_quote_volume"
        ],
        "date_var": [
            "open_time", "close_time"
        ]
    }
}

FTX_PAIRS = ['1INCH-PERP', 'AAVE-PERP', 'ADA-PERP', 'AGLD-PERP', 'ALCX-PERP', 'ALGO-PERP', 'ALICE-PERP',
             'ALPHA-PERP', 'ALT-PERP', 'AMPL-PERP', 'ANC-PERP', 'APE-PERP', 'AR-PERP', 'ASD-PERP',
             'ATLAS-PERP', 'ATOM-PERP', 'AUDIO-PERP', 'AVAX-PERP', 'AXS-PERP', 'BADGER-PERP', 'BAL-PERP',
             'BAND-PERP', 'BAO-PERP', 'BAT-PERP', 'BCH-PERP', 'BIT-PERP', 'BNB-PERP', 'BNT-PERP',
             'BOBA-PERP', 'BRZ-PERP', 'BSV-PERP', 'BTC-PERP', 'BTT-PERP', 'C98-PERP', 'CAKE-PERP',
             'CEL-PERP', 'CELO-PERP', 'CHR-PERP', 'CHZ-PERP', 'CLV-PERP', 'COMP-PERP', 'CONV-PERP',
             'CREAM-PERP', 'CRO-PERP', 'CRV-PERP', 'CUSDT-PERP', 'CVC-PERP', 'CVX-PERP', 'DASH-PERP',
             'DAWN-PERP', 'DEFI-PERP', 'DENT-PERP', 'DMG-PERP', 'DODO-PERP', 'DOGE-PERP', 'DOT-PERP',
             'DRGN-PERP', 'DYDX-PERP', 'EDEN-PERP', 'EGLD-PERP', 'ENJ-PERP', 'ENS-PERP', 'EOS-PERP',
             'ETC-PERP', 'ETH-PERP', 'EXCH-PERP', 'FIDA-PERP', 'FIL-PERP', 'FLM-PERP', 'FLOW-PERP',
             'FTM-PERP', 'FTT-PERP', 'FXS-PERP', 'GAL-PERP', 'GALA-PERP', 'GLMR-PERP', 'GMT-PERP',
             'GRT-PERP', 'GST-PERP', 'HBAR-PERP', 'HNT-PERP', 'HOLY-PERP', 'HOT-PERP', 'HT-PERP',
             'HUM-PERP', 'ICP-PERP', 'ICX-PERP', 'IMX-PERP', 'IOST-PERP', 'IOTA-PERP', 'JASMY-PERP',
             'KAVA-PERP', 'KBTT-PERP', 'KIN-PERP', 'KNC-PERP', 'KSHIB-PERP', 'KSM-PERP', 'KSOS-PERP',
             'LEO-PERP', 'LINA-PERP', 'LINK-PERP', 'LOOKS-PERP', 'LRC-PERP', 'LTC-PERP', 'MANA-PERP',
             'MAPS-PERP', 'MATIC-PERP', 'MCB-PERP', 'MEDIA-PERP', 'MER-PERP', 'MID-PERP', 'MINA-PERP',
             'MKR-PERP', 'MNGO-PERP', 'MOB-PERP', 'MTA-PERP', 'MTL-PERP', 'MVDA10-PERP', 'MVDA25-PERP',
             'NEAR-PERP', 'NEO-PERP', 'OKB-PERP', 'OMG-PERP', 'ONE-PERP', 'ONT-PERP', 'OP-PERP',
             'ORBS-PERP', 'OXY-PERP', 'PAXG-PERP', 'PEOPLE-PERP', 'PERP-PERP', 'POLIS-PERP', 'PRIV-PERP',
             'PROM-PERP', 'PUNDIX-PERP', 'QTUM-PERP', 'RAMP-PERP', 'RAY-PERP', 'REEF-PERP', 'REN-PERP',
             'RNDR-PERP', 'RON-PERP', 'ROOK-PERP', 'ROSE-PERP', 'RSR-PERP', 'RUNE-PERP', 'SAND-PERP',
             'SC-PERP', 'SCRT-PERP', 'SECO-PERP', 'SHIB-PERP', 'SHIT-PERP', 'SKL-PERP', 'SLP-PERP',
             'SNX-PERP', 'SOL-PERP', 'SOS-PERP', 'SPELL-PERP', 'SRM-PERP', 'SRN-PERP', 'STEP-PERP',
             'STMX-PERP', 'STORJ-PERP', 'STX-PERP', 'SUSHI-PERP', 'SXP-PERP', 'THETA-PERP', 'TLM-PERP',
             'TOMO-PERP', 'TONCOIN-PERP', 'TRU-PERP', 'TRX-PERP', 'TRYB-PERP', 'TULIP-PERP', 'UNI-PERP',
             'UNISWAP-PERP', 'USDT-PERP', 'USTC-PERP', 'VET-PERP', 'WAVES-PERP', 'XAUT-PERP', 'XEM-PERP',
             'XLM-PERP', 'XMR-PERP', 'XRP-PERP', 'XTZ-PERP', 'YFI-PERP', 'YFII-PERP', 'ZEC-PERP',
             'ZIL-PERP', 'ZRX-PERP']

BINANCE_PAIRS = ['BTCUSDT', 'ETHUSDT', 'BCHUSDT', 'XRPUSDT', 'EOSUSDT', 'LTCUSDT', 'TRXUSDT', 'ETCUSDT',
                 'LINKUSDT', 'XLMUSDT', 'ADAUSDT', 'XMRUSDT', 'DASHUSDT', 'ZECUSDT', 'XTZUSDT', 'BNBUSDT',
                 'ATOMUSDT', 'ONTUSDT', 'IOTAUSDT', 'BATUSDT', 'VETUSDT', 'NEOUSDT', 'QTUMUSDT',
                 'IOSTUSDT', 'THETAUSDT', 'ALGOUSDT', 'ZILUSDT', 'KNCUSDT', 'ZRXUSDT', 'COMPUSDT',
                 'OMGUSDT', 'DOGEUSDT', 'SXPUSDT', 'KAVAUSDT', 'BANDUSDT', 'RLCUSDT', 'WAVESUSDT',
                 'MKRUSDT', 'SNXUSDT', 'DOTUSDT', 'DEFIUSDT', 'YFIUSDT', 'BALUSDT', 'CRVUSDT', 'TRBUSDT',
                 'RUNEUSDT', 'SUSHIUSDT', 'SRMUSDT', 'EGLDUSDT', 'SOLUSDT', 'ICXUSDT', 'STORJUSDT',
                 'BLZUSDT', 'UNIUSDT', 'AVAXUSDT', 'FTMUSDT', 'HNTUSDT', 'ENJUSDT', 'FLMUSDT', 'TOMOUSDT',
                 'RENUSDT', 'KSMUSDT', 'NEARUSDT', 'AAVEUSDT', 'FILUSDT', 'RSRUSDT', 'LRCUSDT', 'MATICUSDT',
                 'OCEANUSDT', 'CVCUSDT', 'BELUSDT', 'CTKUSDT', 'AXSUSDT', 'ALPHAUSDT', 'ZENUSDT', 'SKLUSDT',
                 'GRTUSDT', '1INCHUSDT', 'CHZUSDT', 'SANDUSDT', 'ANKRUSDT', 'BTSUSDT', 'LITUSDT', 'UNFIUSDT',
                 'REEFUSDT', 'RVNUSDT', 'SFPUSDT', 'XEMUSDT', 'BTCSTUSDT', 'COTIUSDT', 'CHRUSDT', 'MANAUSDT',
                 'ALICEUSDT', 'HBARUSDT', 'ONEUSDT', 'LINAUSDT', 'STMXUSDT', 'DENTUSDT', 'CELRUSDT', 'HOTUSDT',
                 'MTLUSDT', 'OGNUSDT', 'NKNUSDT', 'SCUSDT', 'DGBUSDT', '1000SHIBUSDT', 'ICPUSDT', 'BAKEUSDT',
                 'GTCUSDT', 'BTCDOMUSDT', 'TLMUSDT', 'IOTXUSDT', 'AUDIOUSDT', 'RAYUSDT', 'C98USDT', 'MASKUSDT',
                 'ATAUSDT', 'DYDXUSDT', '1000XECUSDT', 'GALAUSDT', 'CELOUSDT', 'ARUSDT', 'KLAYUSDT', 'ARPAUSDT',
                 'CTSIUSDT', 'LPTUSDT', 'ENSUSDT', 'PEOPLEUSDT', 'ANTUSDT', 'ROSEUSDT', 'DUSKUSDT', 'FLOWUSDT',
                 'IMXUSDT', 'API3USDT', 'GMTUSDT', 'APEUSDT', 'BTCUSDT_220624', 'ETHUSDT_220624', 'BNXUSDT',
                 'WOOUSDT', 'FTTUSDT', 'JASMYUSDT', 'DARUSDT', 'GALUSDT', 'OPUSDT']
