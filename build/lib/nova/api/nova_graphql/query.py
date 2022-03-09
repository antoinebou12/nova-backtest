from gql import gql


class GraphQuery:
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
