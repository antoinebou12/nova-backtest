from nova.clients.gate import Gate
from decouple import config


client = Gate(
    key=config("gateAPIKey"),
    secret=config("gateAPISecret"),
)

data = client.get_pairs()



