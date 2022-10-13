from nova.api.client import NovaAPI
from decouple import config


def test_create_bot(
        name: str,
        exchange: str,
        max_down: float,
        bankroll: float,
        strategy: str,
        exchange_key: str,
        pairs: list
):

    nova_client = NovaAPI(config('NovaAPISecret'))

    data = nova_client.create_bot(
        name=name,
        exchange=exchange,
        max_down=max_down,
        bankroll=bankroll,
        strategy=strategy,
        exchange_key=exchange_key,
        pairs=pairs
    )







