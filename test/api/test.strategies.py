from nova.api.nova_client import NovaClient
from decouple import config

nova_client = NovaClient(config('NovaAPISecret'))

# Create
nova_client.create_strategy(
    name="",
    candle="",
    avg_return_e=3,
    avg_return_r=4
)

# Read
nova_client.read_strategy()

# Update
nova_client.update_strategy()

# Delete
nova_client.delete_strategy()
