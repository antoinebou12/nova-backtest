from nova.api.nova_client import NovaClient
from decouple import config

nova_client = NovaClient(config('NovaAPISecret'))
