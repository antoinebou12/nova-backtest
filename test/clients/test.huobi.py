from nova.clients.huobi import Huobi
from decouple import config


client = Huobi(
    key=config("huobiAPIKey"),
    secret=config("huobiAPISecret")
)


data = client.get_contract_record(pair="usdt")

# data = client.get_contract_info()
