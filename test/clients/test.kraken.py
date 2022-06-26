from nova.clients.kraken import Kraken
from decouple import config


client = Kraken(
    key=config("krakenAPIKey"),
    secret=config("krakenAPISecret")
)

instrument = client.get_instrument()
account = client.get_account()

