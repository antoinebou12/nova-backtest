from nova.clients.okx import OKX
from decouple import config


client = OKX(
    key=config("okxAPYKey"),
    secret=config("okxAPISecret"),
    pass_phrase=config("okxPassPhrase")
)


data = client.get_status()

data = client.get_balances()

data = client.get_positions()


