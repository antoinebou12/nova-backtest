from decouple import config
from nova.utils.strategy import RandomStrategy
from nova.utils.helpers import is_opening_candle
import time
import asyncio
from datetime import datetime


def asserts_computed_profit(exchange: str,
                            list_pair: list
                            ):
    bot = RandomStrategy(
        exchange=exchange,
        key=config(f"{exchange}TestAPIKey"),
        secret=config(f"{exchange}TestAPISecret"),
        passphrase='',
        nova_api_key=config("NovaAPISecret"),
        bot_id='ROBOT1',
        quote_asset='USDT',
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

    start_bk = bot.client.get_token_balance(quote_asset=bot.quote_asset)

    start = time.time()
    print(f'Fetching historical data', "\U000023F3", end="\r")
    bot.prod_data = asyncio.run(bot.client.get_prod_data(
        list_pair=bot.list_pair,
        interval=bot.candle,
        nb_candles=bot.historical_window,
        current_state=None
    ))
    print(f'Historical data downloaded', "\U00002705")
    # Run bot during 10min
    while time.time() - start < 60 * 2:

        if is_opening_candle(interval=bot.candle):
            print(f'------- time : {datetime.utcnow()} -------\nNew candle opens')
            print("Fetching Latest Data", "\U000023F3", end="\r")
            bot.prod_data = asyncio.run(bot.client.get_prod_data(
                list_pair=bot.list_pair,
                interval=bot.candle,
                nb_candles=bot.historical_window,
                current_state=bot.prod_data
            ))
            print(f"Data Updated", "\U00002705")

            if len(bot.position_opened) > 0:
                # verify positions (reach tp or sl)
                bot.verify_positions()

                # check exit signals and perform actions
                bot.exiting_positions()

            # check entry signals and perform actions
            bot.entering_positions()

    bot.exit_probability = 1
    bot.exiting_positions()

    expected_realized_pnl = bot.realizedPNL
    realized_pnl = start_bk - bot.client.get_token_balance(quote_asset=bot.quote_asset)

    print(expected_realized_pnl)
    print(realized_pnl)

    assert abs(expected_realized_pnl) * (1 - 0.01) < abs(realized_pnl) < abs(expected_realized_pnl * (1 + 0.01)), 'wrong profit'

    print(f"Test computed profit for {exchange.upper()} successful")


def test_computed_profit():

    all_tests = [
        {
            'exchange': 'bybit',
            'list_pair': ['BTCUSDT', 'ETHUSDT'],
        }
    ]

    for _test in all_tests:

        asserts_computed_profit(
            exchange=_test['exchange'],
            list_pair=_test['list_pair']

        )


test_computed_profit()
