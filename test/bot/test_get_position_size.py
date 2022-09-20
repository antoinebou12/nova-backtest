from nova.utils.bot import Bot
from decouple import config


def asserts_get_position_size(exchange: str,
                              quote_asset: str,
                              list_pair: list):

    bot = Bot(
            exchange=exchange,
            key=config(f"{exchange}APIKey"),
            secret=config(f"{exchange}APISecret"),
            nova_api_key=config("NovaAPISecret"),
            bot_id='ROBOT1',
            bot_name='TEST_BOT',
            quote_asset=quote_asset,
            candle='15m',
            historical_window=100,
            list_pair=list_pair,
            bankroll=1000,
            leverage=2,
            max_pos=6,
            max_down=0.3,
            max_hold=12,
            limit_time_execution=15,
            telegram_notification=False,
            telegram_bot_token='',
            telegram_bot_chat_id='',
            testnet=True,
            geometric_size=False
    )

    size_amount_1 = bot.get_position_size()
    assert size_amount_1 == 50


def test_get_position_size():
    all_tests = [
        {
            'exchange': 'binance',
            'quote_asset': 'USDT',
            'list_pair': ['BTCUSDT', 'ETHUSDT']
        }
    ]

    for _test in all_tests:
        asserts_get_position_size(
            exchange=_test['exchange'],
            quote_asset=_test['quote_asset'],
            list_pair=_test['list_pair']
        )


test_get_position_size()
