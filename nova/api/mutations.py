from gql import gql


class Mutations:

    @staticmethod
    def create_pair():
        return gql(
            """
            mutation createPair($input: PairInput!){
                createPair(input: $input) {
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
            """)

    @staticmethod
    def update_pair():
        return gql(
            """
            mutation updatePair($input: PairInput!){
                updatePair(input: $input){
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
            """)

    @staticmethod
    def delete_pair():
        return gql(
            """
            mutation deletePair($pairId: ObjectId!){
                deletePair(pairId: $pairId)
            }
            """)

    @staticmethod
    def create_strategy():
        return gql(
            """
                mutation createStrategy($input: StrategyInput!){
                    createStrategy(input: $input) {
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
            """)

    @staticmethod
    def update_strategy():
        return gql(
            """
                mutation updateStrategy($input: StrategyInput!){
                    updateStrategy(input: $input) {
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
            """)

    @staticmethod
    def delete_strategy():
        return gql(
            """
                mutation deleteStrategy($strategyId: ObjectId!){
                    deleteStrategy(strategyId: $strategyId)
                }
            """)

    @staticmethod
    def create_bot():
        return gql(
            """
                mutation createBot($input: BotInput!) {
                    createBot(input: $input) {
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
                        pairs {
                            pair
                        }
                    }
                }
            """)

    @staticmethod
    def update_bot():
        return gql(
            """
                mutation updateBot($input: BotInput!) {
                    updateBot(input: $input) {
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
                        pairs {
                            pair
                        }
                    }
                }
            """)

    @staticmethod
    def delete_bot():
        return gql(
            """
                mutation deleteBot($botId: ObjectId!) {
                    deleteBot(botId: $botId)
                }
            """)

    @staticmethod
    def create_position():
        return gql(
            """
            mutation createPosition($name: String!, $input: PositionInput!) {
                createPosition(name: $name, input: $input) {
                    _id
                }
            }
            """)
        
    @staticmethod
    def update_position():
        return gql(
            """
            mutation updatePosition($input: PositionInput!){
                updatePosition(input: $input){
                    _id
                }
            }
            """)

    @staticmethod
    def delete_position():
        return gql(
            """
            mutation deletePosition($positionId: ObjectId!){
                deletePosition(positionId: $positionId)
            }
            """
        )
