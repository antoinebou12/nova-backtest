from gql import gql


class GraphMutation:

    @staticmethod
    def create_pair():
        return gql(
            """
            mutation createPair($input: PairInput!){
                createPair(input: $input) {
                    _id
                    name
                }
            }
            """
        )

    @staticmethod
    def delete_pair():
        return gql(
            """
            mutation deletePair($pairId: ObjectId!){
                deletePair(pairId: $pairId)
            }
            """
        )

    @staticmethod
    def update_pair():
        return gql(
            """
            mutation updatePair($input: PairInput!){
                updatePair(input: $input){
                    _id
                    name
                }
            }
            """
        )

    @staticmethod
    def create_strategy():
        return gql(
        """
            mutation createStrategy($input: StrategyInput!){
                createStrategy(input: $input) {
                    _id
                    name
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
    def update_strategy():
        return gql(
            """
                mutation editStrategy($input: StrategyInput!){
                    editStrategy(input: $input) {
                        _id
                        name
                    }
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
