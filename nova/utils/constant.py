STD_CANDLE_FORMAT = [
    'open_time', 'open', 'high', 'low', 'close', 'volume', 'close_time'
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
    }

}
