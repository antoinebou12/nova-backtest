from nova.clients.kucoin import Kucoin
from decouple import config


client = Kucoin(
    key=config("kucoinAPIKey"),
    secret=config("kucoinAPISecret"),
    pass_phrase=config("kucoinPassPhrase")
)

data = client.get_account()

data = client.get_pairs()

