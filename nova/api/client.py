from nova.api.mutations import Mutations
from nova.api.queries import Queries
from gql.transport.aiohttp import AIOHTTPTransport
from gql import Client
from typing import Union
import re


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

    def create_pair(self, value: str, name: str, fiat: str, strategies: list, exchanges: list) -> dict:
        return self._client.execute(
            document=Mutations.create_pair(),
            variable_values={
                "input": {
                    "value": value,
                    "name": name,
                    "fiat": fiat,
                    "available_strategy": strategies,
                    "available_exchange": exchanges
                }
            }
        )['createPair']

    def read_pairs(self, pair_id: str = None) -> Union[dict, list]:
        data = self._client.execute(
            document=Queries.read_pairs(pair_id=pair_id)
        )
        if pair_id:
            return data['pair']
        else:
            return data['pairs']

    def update_pair(self,
                    pair_id: str,
                    strategies: list,
                    exchanges: list
                    ):
        """
        Note: We can only update the strategies
        Args:
            pair_id:
            strategies:
            exchanges:
        Returns:
        """

        original_value = self.read_pairs(pair_id=pair_id)

        for exchange in exchanges:
            for key, value in exchange.items():
                if key == 'add':
                    original_value['available_exchange'].append(value)
                elif key == 'remove':
                    original_value['available_exchange'].remove(value)

        for strategy in strategies:
            for _key, _value in strategy.items():
                if _key == 'add':
                    original_value['available_strategy'].append({"name": _value})
                elif _key == 'remove':
                    original_value['available_strategy'].remove({"name": _value})

        return self._client.execute(
            document=Mutations.update_pair(),
            variable_values={
                "input": {
                    "id": pair_id,
                    "value": original_value['value'],
                    "name": original_value['name'],
                    "fiat": original_value['fiat'],
                    "available_strategy": original_value['available_strategy'],
                    "available_exchange": original_value['available_exchange']
                }
            }
        )['updatePair']

    def delete_pair(self, pair_id: str) -> dict:
        return self._client.execute(
            document=Mutations.delete_pair(),
            variable_values={
                "pairId": {
                    'id': pair_id
                }
            }
        )['deletePair']

    def create_strategy(self,
                        name: str,
                        start_time: int,
                        end_time: int,
                        description: str,
                        candles: str,
                        leverage: int,
                        max_position: int,
                        trades: int,
                        day_underwater: int,
                        ratio_winning: float,
                        ratio_sortino: float,
                        ratio_sharp: float,
                        max_down: float,
                        monthly_fee: float,
                        avg_profit: float,
                        avg_hold_time: float,
                        score: float
                        ) -> dict:

        return self._client.execute(
            document=Mutations.create_strategy(),
            variable_values={
                "input": {
                    "name": name,
                    "backtestStartAt": start_time,
                    "backtestEndAt": end_time,
                    "description": description,
                    "version": "V1",
                    "candles": candles,
                    "leverage": leverage,
                    "maxPosition": max_position,
                    "trades": trades,
                    "maxDayUnderwater": day_underwater,
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
        )

    def read_strategies(self, name: str = None) -> Union[dict, list]:
        data = self._client.execute(
            document=Queries.read_strategies(name=name)
        )
        if name:
            return data['strategyByName']
        else:
            return data['strategies']

    def update_strategy(self,
                        name: str,
                        description: str = None,
                        start_time: int = None,
                        end_time: int = None,
                        leverage: int = None,
                        max_position: int = None,
                        trades: int = None,
                        day_underwater: int = None,
                        ratio_winning: float = None,
                        ratio_sortino: float = None,
                        ratio_sharp: float = None,
                        max_down: float = None,
                        monthly_fee: float = None,
                        avg_profit: float = None,
                        avg_hold_time: float = None,
                        score: float = None
                        ) -> dict:

        info = self.read_strategies(name=name)
        nb = [int(s) for s in re.findall(r'\d+', info['version'])][0] + 1
        new_version = f'V{nb}'

        return self._client.execute(
            document=Mutations.update_strategy(),
            variable_values={
                'input': {
                    "id": info['_id'],
                    "name": name,
                    "backtestStartAt": start_time if start_time is not None else info['backtestStartAt'],
                    "backtestEndAt": end_time if end_time is not None else info['backtestEndAt'],
                    "description": description if description is not None else info['description'],
                    "version": new_version,
                    "candles": info['candles'],
                    "leverage": leverage if leverage is not None else info['leverage'],
                    "maxPosition": max_position if max_position is not None else info['maxPosition'],
                    "trades": trades if trades is not None else info['trades'],
                    "maxDayUnderwater": day_underwater if day_underwater is not None else info['maxDayUnderwater'],
                    "ratioWinning": ratio_winning if ratio_winning is not None else info['ratioWinning'],
                    "ratioSharp": ratio_sharp if ratio_sharp is not None else info['ratioSharp'],
                    "ratioSortino": ratio_sortino if ratio_sortino is not None else info['ratioSortino'],
                    "maxDrawdown": max_down if max_down is not None else info['maxDrawdown'],
                    "monthlyFee": monthly_fee if monthly_fee is not None else info['monthlyFee'],
                    "avgProfit": avg_profit if avg_profit is not None else info['avgProfit'],
                    "avgHoldTime": avg_hold_time if avg_hold_time is not None else info['avgHoldTime'],
                    "score": score if score is not None else info['score']
                }
            }
        )['updateStrategy']

    def delete_strategy(self, params) -> dict:
        return self._client.execute(
            document=Mutations.delete_strategy(),
            variable_values=params
        )

    def create_bot(self,
                   exchange: str,
                   max_down: float,
                   bankroll: float,
                   strategy: str,
                   exchange_key_name: str,
                   pairs: list) -> dict:

        return self._client.execute(
            document=Mutations.create_bot(),
            variable_values={
                'input': {
                    'exchange': exchange,
                    'maxDown': max_down,
                    'bankRoll': bankroll,
                    'totalProfit': 0,
                    'status': 'offline',
                    'strategy': {
                        'name': strategy
                    },
                    'exchangeKey': {
                        'name': exchange_key_name
                    },
                    'pairs': [{'pair': pair} for pair in pairs],
                }
            }
        )['createBot']

    def read_bots(self, bot_id: str = None) -> dict:
        data = self._client.execute(
            document=Queries.read_bots(bot_id=bot_id)
        )
        if bot_id:
            return data['bot']
        else:
            return data['bots']

    def update_bot(self,
                   bot_id: str,
                   max_down: float = None,
                   bankroll: float = None,
                   status: str = None,
                   new_exchange_key: str = None,
                   pairs: list = None
                   ) -> dict:

        info = self.read_bots(bot_id=bot_id)

        for pair in pairs:
            for _key, _value in pair.items():
                if _key == 'add':
                    info['pairs'].append({"pair": _value})
                elif _key == 'remove':
                    info['pairs'].remove({"pair": _value})

        return self._client.execute(
            document=Mutations.update_bot(),
            variable_values={
                'input': {
                    'id': bot_id,
                    'maxDown': max_down if max_down is not None else info['maxDown'],
                    'bankRoll': bankroll if bankroll is not None else info['bankRoll'],
                    'status': status if status is not None else info['status'],
                    'exchangeKey': {
                        'name': new_exchange_key if new_exchange_key is not None else info['exchangeKey']['name']
                    },
                    'pairs': info['pairs']
                }
            }
        )['updateBot']

    def delete_bot(self, bot_id: str) -> dict:
        return self._client.execute(
            document=Mutations.delete_bot(),
            variable_values={
                "botId": {
                    'id': bot_id
                }
            }
        )['deleteBot']

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

        return self._client.execute(
            document=Mutations.create_position(),
            variable_values={
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
        )["createPosition"]
    #
    # def update_position(self,
    #                     pos_id: str,
    #                     pos_type: str,
    #                     state: str,
    #                     entry_price: float,
    #                     exit_price: float,
    #                     exit_type: str,
    #                     profit: float,
    #                     fees: float,
    #                     pair: str):
    #
    #     params = {
    #         "input": {
    #             "id": pos_id,
    #             "type": pos_type,
    #             "state": state,
    #             "entry_price": entry_price,
    #             "exit_price": exit_price,
    #             "exit_type": exit_type,
    #             "profit": profit,
    #             "fees": fees,
    #             "pair": {
    #                 "value": "BTC",
    #                 "name": "Bitcoin",
    #                 "fiat": "USDT",
    #                 "pair": pair,
    #                 "available_exchange": ['binance']
    #             }
    #         }
    #     }
    #
    #     return self._client.execute(
    #         document=Mutation.update_position(),
    #         variable_values=params
    #     )
    #
    # def delete_position(self, position_id: str):
    #     params = {
    #         "positionId": {
    #             'id': position_id
    #         }
    #     }
    #
    #     return self._client.execute(
    #         document=Mutation.delete_position(),
    #         variable_values=params
    #     )
    #
    # def read_position(self, position_id: str):
    #     return self._client.execute(
    #         document=Query.read_position(_position_id=position_id)
    #     )
    #
    # def read_positions(self):
    #     return self._client.execute(
    #         document=Query.read_positions()
    #     )
    #
