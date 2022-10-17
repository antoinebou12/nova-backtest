from decouple import config
from nova.utils.strategy import RandomStrategy
from nova.utils.helpers import is_opening_candle
import asyncio
from multiprocessing import set_start_method
set_start_method('fork')


def asserts_security_close_all_positions(
        exchange: str,
        quote_asset: str,
        list_pair: list
):
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
        telegram_bot_chat_id='',
        entry_l_prob=0.8,
        entry_s_prob=0.8,

    )

    bot.client.setup_account(
        bankroll=bot.bankroll,
        quote_asset=bot.quote_asset,
        leverage=bot.leverage,
        max_down=bot.max_down,
        list_pairs=bot.list_pair
    )

    bot.prod_data = asyncio.run(bot.client.get_prod_data(
        list_pair=bot.list_pair,
        interval=bot.candle,
        nb_candles=bot.historical_window,
        current_state=None
    ))

    done = False

    print('Starting the Loop')

    while not done:

        if is_opening_candle(interval=bot.candle):

            bot.entering_positions()

            bot.security_close_all_positions()

            assert len(bot.position_opened) == 0

            done = True

    print(f"Test security_close_all_positions for {exchange.upper()} successful")


def test_security_close_all_positions():
    all_tests = [
        {
            'exchange': 'binance',
            'quote_asset': 'USDT',
            'list_pair': ['BTCUSDT', 'ETHUSDT']
        }
    ]

    for _test in all_tests:
        asserts_security_close_all_positions(
                exchange=_test['exchange'],
                quote_asset=_test['quote_asset'],
                list_pair=_test['list_pair']
        )


test_security_close_all_positions()
