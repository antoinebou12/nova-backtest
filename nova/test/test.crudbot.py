from nova.api.nova_client import NovaClient
from decouple import config

nova_client = NovaClient(config('NovaAPISecret'))


data = nova_client.read_bot(_bot_id="62522ee98acf3c6a027d9769")