from decouple import config
from nova.utils.strategy import RandomStrategy


def asserts_get_position_size(exchange: str,
                              quote_asset: str,
                              list_pair: list):

    bot = RandomStrategy(
        exchange=exchange,
        key=config(f"{exchange}TestAPIKey"),
        secret=config(f"{exchange}TestAPISecret"),
        passphrase='',
        nova_api_key=config("NovaAPISecret"),
        bot_id='ROBOT1',
        quote_asset=quote_asset,
        candle='1m',
        list_pair=list_pair,
        bankroll=1000,
        leverage=2,
        max_pos=6,
        max_down=0.3,
        telegram_notification=False,
        telegram_bot_token='',
        telegram_bot_chat_id=''
    )

    size_amount_1 = bot.get_position_size()

    # position size should be equal to leverage / max_pos

    estimated = bot.leverage / bot.max_pos * bot.bankroll
    assert size_amount_1 == estimated
    print(f"Test get_position_size for {exchange.upper()} successful")


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
