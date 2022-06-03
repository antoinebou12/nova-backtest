from gql import gql


class GraphQuery:

    @staticmethod
    def read_strategy(_name: str):
        return gql(
            """
            {
                strategyByName (name: "%s") {
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
            """%(_name)
        )

    @staticmethod
    def read_strategies():
        return gql(
            """
            {
                strategies {
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
            """
        )

    @staticmethod
    def read_pair(_pairId: str):
        return gql(
            """
            {
                pair (pairId: "%s") {
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
            """%(_pairId)
        )

    @staticmethod
    def read_pairs():
        return gql(
            """
            {
                pairs {
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
            """
        )


    @staticmethod
    def read_bots():
        return gql('''
        {
            bots {
                _id
                name
            }
        }
        ''')

    @staticmethod
    def read_bot(_bot_id: str):
        return gql('''
        {
            bot(botId: "%s") {
                _id
                name
                exchange
                maxDown
                bankRoll
                status
                totalProfit
                pairs{
                    pair
                }
                strategy{
                    name
                }
            }
        }
        ''' % _bot_id)

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

    @staticmethod
    def read_position(_position_id: str):
        return gql(
            """
               {
                    position (positionId: "%s") {
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
           """%(_position_id)
        )
