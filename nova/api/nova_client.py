from gql import Client
from gql.transport.aiohttp import AIOHTTPTransport
import sys

from nova.api.nova_graphql.mutation import GraphMutation
from nova.api.nova_graphql.query import GraphQuery

from nova.api.entity import Bot, Strategy
from nova.api.structure import Structure


class NovaClient:
    # Entity mapping
    bots_map = dict.fromkeys(['id', 'bot'])

    def __init__(self, api_secret=None) -> None:
        self._api_secret = api_secret
        self._headers = {"Authorization": f"Bearer {api_secret}"}
        self._transport = AIOHTTPTransport(url='https://novalabs-api.herokuapp.com/graphql',
                                           headers=self._headers)
        self._client = Client(transport=self._transport,
                              fetch_schema_from_transport=True)

    def create_bot(self, exchange: str, strategy: str) -> dict:
        query = GraphMutation.create_bot_query()
        variables = '{ "input": { "exchange": "' + exchange + '", "strategy": { "name": "' + strategy + '" } } }'
        return self._client.execute(query, variable_values=variables)

    def get_all_bots(self) -> dict:
        return self._client.execute(GraphQuery.bots())


client = NovaClient(api_secret='deleted')

result = client.get_all_bots()
bot_nbr = len(result['bots'])

for bot in result['bots']:
    object_id = bot['_id']
    name = bot['name']
    exchange = bot['exchange']
    strategy_id = bot['strategy']['_id']

    strategy = Strategy(object_id=strategy_id)
    test = Bot(object_id=object_id, name=name, exchange=exchange, strategy=strategy, positions=[])
    Structure.bots_map[object_id] = test

for key, value in Structure.bots_map.items():
    print(key, 'correspond to', value)
    print(value.get_name())
