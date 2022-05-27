from gql import Client
from gql.transport.aiohttp import AIOHTTPTransport

from nova.api.mutation import GraphMutation as Mutation
from nova.api.query import GraphQuery as Query


class NovaClient:

    def __init__(self, api_secret=None) -> None:
        self._api_secret = api_secret
        self._headers = {"Authorization": f"Bearer {api_secret}"}
        self._transport = AIOHTTPTransport(
            url='https://api.novalabs.ai/graphql',
            headers=self._headers
        )
        self._client = Client(
            transport=self._transport,
            fetch_schema_from_transport=True
        )

    # Pairs
    def create_pairs(
        self,
        value: str,
        name: str,
        fiat: str,
        strategies: list,
        exchanges: list
    ) -> dict:

        params = {
            "input": {
                "value": value,
                "name": name,
                "fiat": fiat,
                "available_strategy": strategies,
                "available_exchanges": exchanges
            }
        }

        data = self._client.execute(
            Mutation.create_pair_query(),
            variable_values=params
        )
        return data

    def read_pairs(self) -> dict:
        return self._client.execute(Query.read_pairs())

    def update_pairs(self) -> dict:
        pass

    def delete_pairs(self, pair_id: str) -> dict:
        params = {
            "pairId": {
                'id': pair_id
            }
        }

        self._client.execute(Mutation.delete_pair(), variable_values=params)

    def create_strategy(self,
                        name: str,
                        candle: str,
                        avg_return_e: float,
                        avg_return_r: float) -> dict:
        params = {
            "input": {
                "name": name,
                "candles": candle,
                "avg_expd_return": avg_return_e,
                "avg_reel_return": avg_return_r
            }
        }
        return self._client.execute(Mutation.create_strategy(), variable_values=params)

    def read_strategy(self) -> dict:
        return self._client.execute(Query.read_strategy())

    def update_strategy(self) -> dict:
        pass

    def delete_strategy(self) -> dict:
        pass

    def create_bot(self,
                   exchange: str,
                   max_down: float,
                   bankroll: float,
                   strategy: str) -> dict:
        params = {
            "input": {
                "exchange": exchange,
                "maxDown": max_down,
                "bankRoll": bankroll,
                "strategy": {
                    "name": strategy
                },
            }
        }
        data = self._client.execute(Mutation.create_bot_query(), variable_values=params)
        return data

    def read_bots(self):
        return self._client.execute(Query.read_bots())

    def read_bot(self, _bot_id) -> dict:
        return self._client.execute(Query.read_bot(_bot_id))

    def update_bot(self):
        pass

    def delete_bot(self):
        pass

    def create_position(self,
                        bot_name: str,
                        post_type: str,
                        value: float,
                        state: str,
                        entry_price: float,
                        take_profit: float,
                        stop_loss: float,
                        pair: str):
        
        params = {
            "name": bot_name,
            "input": {
                "type": post_type,
                "value": value,
                "state": state,
                "entry_price": entry_price,
                "take_profit": take_profit,
                "stop_loss": stop_loss,
                "pair": {
                    "pair": pair
                }
            }
        }
        data = self._client.execute(
            Mutation.new_bot_position_query(),
            variable_values=params
        )
        return data

    def read_positions(self):
        return self._client.execute(Query.read_positions())

    def update_position(self,
                        pos_id: str,
                        pos_type: str,
                        state: str,
                        entry_price: float,
                        exit_price: float,
                        exit_type: str,
                        profit: float,
                        fees: float,
                        pair: str):

        params = {
            "input": {
                "id": pos_id,
                "type": pos_type,
                "state": state,
                "entry_price": entry_price,
                "exit_price": exit_price,
                "exit_type": exit_type,
                "profit": profit,
                "fees": fees,
                "pair": {
                    "name": pair
                }
            }
        }

        data = self._client.execute(
            Mutation.update_bot_position_query(),
            variable_values=params
        )

        return data

    def delete_positions(self, position_id: str):
        params = {
            "positionId": {
                'id': position_id
            }
        }

        self._client.execute(Mutation.delete_position(), variable_values=params)
        pass
