from decouple import config
from nova.utils.strategy import RandomStrategy
from multiprocessing import set_start_method
set_start_method('fork')


def asserts_production_run(
        exchange: str,
        quote_asset: str,
        list_pair: list
):
    bot = RandomStrategy(
        exchange=exchange,
        key=config(f"{exchange}APIKey"),
        secret=config(f"{exchange}APISecret"),
        passphrase='',
        nova_api_key=config("NovaAPISecret"),
        bot_id='ROBOT1',
        quote_asset=quote_asset,
        candle='1m',
        list_pair=list_pair,
        bankroll=150,
        leverage=2,
        max_pos=6,
        max_down=0.2,
        telegram_notification=True,
        telegram_bot_token=config('token_vmc_binance_bot'),
        telegram_bot_chat_id=config('chat_vmc_binance'),
        tp_sl_delta=0.01,
        testnet=False
    )

    bot.production_run()


def test_production_run():
    all_tests = [
        {
            'exchange': 'binance',
            'quote_asset': 'USDT',
            'list_pair': ['BTCUSDT', 'ETHUSDT']
        }
    ]

    for _test in all_tests:
        asserts_production_run(
                exchange=_test['exchange'],
                quote_asset=_test['quote_asset'],
                list_pair=_test['list_pair']
        )


test_production_run()
