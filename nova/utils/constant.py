STD_CANDLE_FORMAT = [
    'open_time', 'open', 'high', 'low', 'close', 'volume', 'close_time'
]

VAR_NEEDED_FOR_POSITION = [
    'all_entry_time', 'all_entry_point', 'all_entry_price',
    'all_exit_time', 'all_exit_point', 'all_tp', 'all_sl'
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
    },
    "ftx": {
        "columns": [
            'startTime', 'time', 'open', 'high', 'low', 'close', 'volume'
        ],
        "num_var": [
            'open', 'high', 'low', 'close', 'volume'
        ]
    },
    "bybit": {
        "columns": [
            'open_time', 'open', 'high', 'low', 'close', 'volume', 'turnover'
        ],
        "num_var": [
            'open', 'high', 'low', 'close', 'volume', 'turnover'
        ]
    },
    "kraken": {
        "columns": [
            'open_time', 'open', 'high', 'low', 'close', 'volume'
        ],
        "num_var": [
            'open', 'high', 'low', 'close', 'volume',
        ],
        "date_var": ["open_time", "close_time"]
    },
    "coinbase": {
        "columns": [
            'open_time', 'low', 'high', 'open', 'close', 'volume'
        ],
        "num_var": [
            'open', 'high', 'low', 'close', 'volume',
        ],
        "date_var": ["open_time", "close_time"]
    },
    "kucoin": {
        "columns": [
            'open_time', 'open', 'high', 'low', 'close', 'volume'
        ],
        "num_var": [
            'open', 'high', 'low', 'close', 'volume',
        ],
        "date_var": ["open_time", "close_time"]
    },
    "okx": {
        "columns": [
            'open_time', 'open', 'high', 'low', 'close', 'volume', 'volume_quote'
        ],
        "num_var": [
            'open', 'high', 'low', 'close', 'volume', 'volume_quote'
        ],
        "date_var": ["open_time", "close_time"]
    }

}

