from nova.utils.bot import Bot
from decouple import config

params = {
    'exchange': 'binance',
    'key': config(f"binanceAPIKey"),
    'secret': config(f"binanceAPISecret"),
    'nova_api_key': config("NovaAPISecret"),
    'bot_id': 'ROBOT1',
    'bot_name': 'ROBOT',
    'based_asset': 'USDT',
    'candle': '5m',
    'historical_window': 100,
    'list_pair': ['BTCUSDT', 'ETHUSDT'],
    'bankroll': 500.0,
    'position_size': 1/10,
    'geometric_size': True,
    'max_pos': 10,
    'max_down': 0.2,
    'max_hold': 12,
    'telegram_notification': False,
    'bot_token': 'token',
    'bot_chat_id': 'chat_id'
}


def test_get_position_size(
        _params: dict
):

    bot = Bot(
            exchange=_params['exchange'],
            key=_params['key'],
            secret=_params['secret'],
            nova_api_key=_params['nova_api_key'],
            bot_id=_params['bot_id'],
            bot_name=_params['bot_name'],
            based_asset=_params['based_asset'],
            candle=_params['candle'],
            historical_window=_params['historical_window'],
            list_pair=_params['list_pair'],
            bankroll=_params['bankroll'],
            position_size=_params['position_size'],
            geometric_size=_params['geometric_size'],
            max_pos=_params['max_pos'],
            max_down=_params['max_down'],
            max_hold=_params['max_hold'],
            telegram_notification=_params['telegram_notification'],
            bot_token=_params['bot_token'],
            bot_chat_id=_params['bot_chat_id']
    )

    size_amount_1 = bot.get_position_size()
    assert size_amount_1 == 50


test_get_position_size(
    _params=params
)
