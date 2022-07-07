from nova.clients.gate import Gate
from decouple import config


client = Gate(
    key=config("coinbaseAPIKey"),
    secret=config("coinbaseAPISecret"),
)
