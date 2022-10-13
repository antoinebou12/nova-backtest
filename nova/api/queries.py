from gql import gql


class Queries:

    @staticmethod
    def read_pairs(pair_id: str = None):

        to_add = "pairs " if pair_id is None else f'pair (pairId: "{pair_id}") '

        return gql(
            """
            {
                %s{
                    _id
                    value
                    name
                    fiat
                    pair
                    available_exchange
                    available_strategy {
                        name
                    }
                }
            }
            """ % to_add
        )

    @staticmethod
    def read_strategies(name: str = None):

        to_add = "strategies " if name is None else f'strategyByName (name: "{name}") '

        return gql(
            """
            {
                %s{
                    _id
                    name
                    backtestStartAt
                    backtestEndAt
                    description
                    version
                    candles
                    leverage
                    maxPosition
                    trades
                    maxDayUnderwater
                    ratioWinning
                    ratioSortino
                    ratioSharp
                    maxDrawdown
                    monthlyFee
                    avgProfit
                    avgHoldTime
                    score
                }
            }
            """ % to_add
        )

    @staticmethod
    def read_bots(bot_id: str = None):

        to_add = "bots " if bot_id is None else f'bot (botId: "{bot_id}") '

        return gql(
            '''
            {
                %s{
                    _id
                    name
                    exchange
                    maxDown
                    bankRoll
                    totalProfit
                    status
                    strategy {
                        name
                    }
                    exchangeKey {
                        name
                    }
                    positions{
                        type
                        value
                        state
                    }         
                    pairs {
                        pair
                    }
                }
            }
            ''' % to_add
            )

    @staticmethod
    def read_positions():
        return gql(
            '''
            {
                positions {
                    _id
                    type
                    value
                    state
                    entry_price
                    exit_price
                    take_profit
                    stop_loss
                    exit_type
                    profit
                    fees
                    pair {
                        pair
                    }
                }
            }
            ''')
