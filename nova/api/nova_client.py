from gql import Client
from gql.transport.aiohttp import AIOHTTPTransport

from nova.api.nova_graphql.mutation import GraphMutation
from nova.api.nova_graphql.query import GraphQuery


class NovaClient:

    def __init__(self, api_secret=None) -> None:
        self._api_secret = api_secret
        self._headers = {"Authorization": f"Bearer {api_secret}"}
        self._transport = AIOHTTPTransport(url='https://novalabs-api.herokuapp.com/graphql',
                                           headers=self._headers)
        self._client = Client(transport=self._transport,
                              fetch_schema_from_transport=True)
        
    def create_pair(self, pair: str) -> dict:
        query = GraphMutation.create_pair_query()
        params = {
            "input": {
                "name": pair
            }
        }
        
        return self._client.execute(query, variable_values=params)
    
    def create_strategy(self, name: str, candle: str, avg_return_e: float, avg_return_r: float) -> dict:
        query = GraphMutation.create_strategy_query()
        
        params = {
            "input": {
                "name": name,
                "candles": candle,
                "avg_expd_return": avg_return_e,
                "avg_reel_return": avg_return_r
            }
        }
        return self._client.execute(query, variable_values=params)

        
    def create_bot(self, name: str, exchange: str, strategy: str) -> dict:
        query = GraphMutation.create_bot_query()
        params = {
            "input": {
                "name": name,
                "exchange": exchange,
                "strategy": {
                    "name": strategy
                },
            }
        }
        return self._client.execute(query, variable_values=params)
    
    
    def create_new_bot_position(self, bot_name: str, post_type: str, value: float,
                                state: str, entry_price: float, take_profit: float, 
                                stop_loss: float, pair: str):
        
        query = GraphMutation.new_bot_position_query()
        params = {
            "name": bot_name,
            "input": {
                "type": post_type,
                "value": value,
                "state": state,
                "entry_price": entry_price,
                "take_profit": take_profit,
                "stop_loss": stop_loss,
                "pair":{
                    "name": pair
                }
            }
        }
        return self._client.execute(query, variable_values=params)
    
    def update_bot_position(self, pos_id: str, state: str,
                            entry_price: float, exit_price: float,
                            exit_type: str, profit: float, fees: float):
        
        query = GraphMutation.update_bot_position_query()
        params = {
            "input": {
                "id": pos_id,
                "state": state,
                "entry_price": entry_price,
                "exit_price": exit_price,
                "exit_type": exit_type,
                "profit": profit,
                "fees": fees,   
            }
        }
        return self._client.execute(query, variable_values=params)    
    
    
    def get_all_bots(self) -> dict:
        return self._client.execute(GraphQuery.bots())
    
    

