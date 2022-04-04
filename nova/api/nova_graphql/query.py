from gql import gql


class GraphQuery:
    
    @staticmethod
    def strategies():
        return gql(
        """
            query 
        """
        )

    
    @staticmethod
    def bots():
        return gql('''
        query getBots {
            bots {
                _id
                name
                exchange
                strategy {
                    _id
                }
                positions {
                    _id
                }
            }
        }
        ''')

    @staticmethod
    def bot(_bot_id: str):
        return gql('''
        {
            bot(botId: "%s") {
                _id
                name
            }
        }
        ''' % _bot_id)

    @staticmethod
    def positions():
        return gql('''
                   
                   ''')
