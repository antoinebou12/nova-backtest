from gql import gql


class GraphMutation:
    @staticmethod
    def create_bot_query():
        return gql("""
            mutation createBot($input: BotInput!) {
                createBot(input: $input) {
                    _id
                    name
                    exchange
                    strategy {
                        _id
                        name
                    }
                }
            }
        """)

    @staticmethod
    def new_bot_position_query():
        return gql("""
                mutation newBotPosition($name: String!, $input: PositionInput!) {
                    newBotPosition(name: $name, input: $input) {
                        name
                        exchange
                        positions {
                            _id
                        }
                    }
                }
            """)
