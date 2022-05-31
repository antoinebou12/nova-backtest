from gql import gql


class GraphQuery:

    @staticmethod
    def read_pairs():
        return gql(
            """
            {
                pairs {
                    _id
                    name
                }
            }
            """
        )

    @staticmethod
    def read_strategy():
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
    def read_bots():
        return gql('''
        query getBots {
            bots {
                _id
                name
                exchange
                maxDown
                bankRoll
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
                pairs{
                    pair
                }
            }
        }
        ''' % _bot_id)

    @staticmethod
    def read_positions():
        return gql(
            '''
            query Positions{
                positions {_id}
            }
            ''')

    @staticmethod
    def read_position(_bot_id: str):
        return gql('''
                   {
                        positions(botId: "%s") {
                            _id
                            name
                            exchange
                            maxDown
                            bankRoll
                        }
                    }
                   ''')
