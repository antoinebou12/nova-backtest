from nova.api.mutation import Mutation
from nova.api.query import Query

from gql.transport.aiohttp import AIOHTTPTransport
from gql import Client


class NovaAPI:

    def __init__(self, api_secret: str):

        self._transport = AIOHTTPTransport(
            url='https://api.novalabs.ai/graphql',
            headers={"Authorization": f"Bearer {api_secret}"}
        )

        self._client = Client(
            transport=self._transport,
            fetch_schema_from_transport=True
        )

    # Strategies
    def create_strategy(self,
                        name: str,
                        start_time: int,
                        end_time: int,
                        version: str,
                        candles: str,
                        leverage: int,
                        max_position: int,
                        trades: int,
                        max_day_underwater: int,
                        ratio_winning: float,
                        ratio_sortino: float,
                        ratio_sharp: float,
                        max_down: float,
                        monthly_fee: float,
                        avg_profit: float,
                        avg_hold_time: float,
                        score: float
                        ) -> dict:
        params = {
            "input": {
                "name": name,
                "backtestStartAt": start_time,
                "backtestEndAt": end_time,
                "version": version,
                "candles": candles,
                "leverage": leverage,
                "maxPosition": max_position,
                "trades": trades,
                "maxDayUnderwater": max_day_underwater,
                "ratioWinning": ratio_winning,
                "ratioSharp": ratio_sortino,
                "ratioSortino": ratio_sharp,
                "maxDrawdown": max_down,
                "monthlyFee": monthly_fee,
                "avgProfit": avg_profit,
                "avgHoldTime": avg_hold_time,
                "score": score
            }
        }

        return self._client.execute(
            document=Mutation.create_strategy(),
            variable_values=params
        )

    def read_strategy(self, strat_name: str) -> dict:
        return self._client.execute(
            document=Query.read_strategy(_name=strat_name)
        )

    def read_strategies(self) -> dict:
        return self._client.execute(
            document=Query.read_strategies()
        )

    def update_strategy(self, params: dict) -> dict:
        return self._client.execute(
            document=Mutation.update_strategy(),
            variable_values=params
        )

    def delete_strategy(self, params) -> dict:
        return self._client.execute(
            document=Mutation.delete_strategy(),
            variable_values=params
        )

    def create_pair(
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
                "available_exchange": exchanges
            }
        }

        data = self._client.execute(
            document=Mutation.create_pair(),
            variable_values=params
        )
        return data

    def delete_pair(self, pair_id: str):
        params = {
            "pairId": {
                'id': pair_id
            }
        }
        self._client.execute(
            document=Mutation.delete_pair(),
            variable_values=params
        )

    def update_pair(self, params: dict):
        self._client.execute(
            document=Mutation.update_pair(),
            variable_values=params
        )

    def read_pair(self, pair_id: str) -> dict:
        return self._client.execute(
            document=Query.read_pair(_pairId=pair_id)
        )

    def read_pairs(self) -> dict:
        return self._client.execute(
            document=Query.read_pairs()
        )

    def create_bot(self,
                   params: dict) -> dict:
        return self._client.execute(
            document=Mutation.create_bot(),
            variable_values=params
        )

    def update_bot(self,
                   params: dict) -> dict:
        return self._client.execute(
            document=Mutation.update_bot(),
            variable_values=params
        )

    def delete_bot(self,
                   id_bot: str) -> dict:
        params = {
            "botId": {
                'id': id_bot
            }
        }
        return self._client.execute(
            document=Mutation.delete_bot(),
            variable_values=params
        )

    def read_bots(self) -> dict:
        return self._client.execute(
            document=Query.read_bots()
        )

    def read_bot(self, _bot_id) -> dict:
        return self._client.execute(
            document=Query.read_bot(_bot_id)
        )

    def create_position(self,
                        bot_name: str,
                        post_type: str,
                        value: float,
                        state: str,
                        entry_price: float,
                        take_profit: float,
                        stop_loss: float,
                        token: str,
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
                    "value": token,
                    "name": "Bitcoin",
                    "fiat": "USDT",
                    "pair": pair,
                    "available_exchange": ['binance']
                }
            }
        }
        return self._client.execute(
            document=Mutation.create_position(),
            variable_values=params
        )

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
                    "value": "BTC",
                    "name": "Bitcoin",
                    "fiat": "USDT",
                    "pair": pair,
                    "available_exchange": ['binance']
                }
            }
        }

        return self._client.execute(
            document=Mutation.update_position(),
            variable_values=params
        )

    def delete_position(self, position_id: str):
        params = {
            "positionId": {
                'id': position_id
            }
        }

        return self._client.execute(
            document=Mutation.delete_position(),
            variable_values=params
        )

    def read_position(self, position_id: str):
        return self._client.execute(
            document=Query.read_position(_position_id=position_id)
        )

    def read_positions(self):
        return self._client.execute(
            document=Query.read_positions()
        )

    def trading_pairs(self):
        pass