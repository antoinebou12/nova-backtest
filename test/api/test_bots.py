from nova.api.client import NovaAPI
from decouple import config


def test_create_bot(
        exchange: str,
        max_down: float,
        bankroll: float,
        strategy: str,
        exchange_key_name: str,
        pairs: list
):

    nova_client = NovaAPI(config('NovaAPISecret'))

    data = nova_client.create_bot(
        exchange=exchange,
        max_down=max_down,
        bankroll=bankroll,
        strategy=strategy,
        exchange_key_name=exchange_key_name,
        pairs=pairs
    )

    print(data)


# test_create_bot(
#     exchange='binance',
#     max_down=0.3,
#     bankroll=1000,
#     strategy='vmc',
#     exchange_key_name='BinanceKeys',
#     pairs=['BTCUSDT']
# )


def test_read_bots(bot_id: str = None):
    nova_client = NovaAPI(config('NovaAPISecret'))

    data = nova_client.read_bots(
        bot_id
    )

    print(data)


# test_read_bots(bot_id="6348442284e89222198883ec")
# test_read_bots()


def test_update_bot(bot_id: str, max_down: float, bankroll: float, status: str, new_exchange_key: str, pairs: list):

    nova_client = NovaAPI(config('NovaAPISecret'))

    data = nova_client.update_bot(
        bot_id=bot_id,
        max_down=max_down,
        bankroll=bankroll,
        status=status,
        new_exchange_key=new_exchange_key,
        pairs=pairs,
    )

    print(data)


test_update_bot(
    bot_id='6348442284e89222198883ec',
    max_down=0.5,
    bankroll=2500,
    status='offline',
    new_exchange_key='Maelito',
    pairs=[{'add': 'ETHUSDT'}],
)


def test_delete_bot(bot_id: str):
    nova_client = NovaAPI(config('NovaAPISecret'))

    data = nova_client.delete_bot(
        bot_id=bot_id
    )

    print(data)


# test_delete_bot(bot_id="634838b684e89222198883c9")


