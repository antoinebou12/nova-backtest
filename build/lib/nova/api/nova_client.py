from gql import Client
from gql.transport.aiohttp import AIOHTTPTransport
import sys

from nova.api.nova_graphql.mutation import GraphMutation
from nova.api.nova_graphql.query import GraphQuery

from nova.api.entity import Bot, Strategy
from nova.api.structure import Structure


class NovaClient:
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
    
    

