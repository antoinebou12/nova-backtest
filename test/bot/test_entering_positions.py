from decouple import config
from nova.utils.strategy import RandomStrategy
from nova.utils.helpers import is_opening_candle
import asyncio
from multiprocessing import set_start_method
set_start_method('fork')


def asserts_entering_positions(
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
        telegram_bot_chat_id=''
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

    while not done:

        if is_opening_candle(interval=bot.candle):

            bot.entering_positions()

            if len(bot.position_opened) > 0:

                variables_expected = ['pair', 'position_type', 'original_position_size', 'current_position_size',
                                      'entry_time', 'tp_id', 'tp_price', 'sl_id', 'sl_price', 'trade_status',
                                      'quantity_exited', 'exit_fees', 'last_exit_time', 'exit_price', 'entry_fees',
                                      'entry_price']

                for key, values in bot.position_opened.items():
                    assert key in bot.list_pair

                    for variable in values.keys():
                        assert variable in variables_expected

                    bot.client.cancel_order(pair=key, order_id=values['tp_id'])
                    bot.client.cancel_order(pair=key, order_id=values['sl_id'])

                    bot.client.exit_market_order(
                        pair=key,
                        type_pos=values['position_type'],
                        quantity=values['current_position_size']
                    )

                done = True

    print(f"Test positions_enter for {exchange.upper()} successful")


def test_entering_positions():
    all_tests = [
        {
            'exchange': 'binance',
            'quote_asset': 'USDT',
            'list_pair': ['BTCUSDT', 'ETHUSDT']
        }
    ]

    for _test in all_tests:
        asserts_entering_positions(
                exchange=_test['exchange'],
                quote_asset=_test['quote_asset'],
                list_pair=_test['list_pair']
        )


test_entering_positions()
