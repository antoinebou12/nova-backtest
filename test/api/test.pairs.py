from nova.api.nova_client import NovaClient
from decouple import config


nova_client = NovaClient(config('NovaAPISecret'))


pair_created = nova_client.create_pairs(
    value='XRP',
    name='XRP',
    fiat='USDT',
    strategies=['vmc', 'ichimoku'],
    exchanges=['binance']
)








