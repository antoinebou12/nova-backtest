from nova.clients.gemini import Gemini
from decouple import config


client = Gemini(
    key=config("geminiAPIKey"),
    secret=config("geminiAPISecret"),
)

# data = client.get_pairs()
data = client.get_balance()
