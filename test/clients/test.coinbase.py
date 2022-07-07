from nova.clients.coinbase import Coinbase
from decouple import config


client = Coinbase(
    key=config("coinbaseAPIKey"),
    secret=config("coinbaseAPISecret"),
    pass_phrase=config("coinbasePassPhrase")
)

data = client.get_account()

for x in data:
    if x['currency'] == "ETH":
        print(x)

# profile id


data = client.get_pairs()
