from nova.api.structure import Structure


class Entity:
    def __init__(self, object_id):
        self.id = object_id

    def __hash__(self):
        return hash(self.id)

    def __eq__(self, other):
        return self.id == other.id


class Strategy(Entity):
    def __init__(self, object_id):
        super().__init__(object_id)


class Position(Entity):
    def __init__(self, object_id):
        super().__init__(object_id)


class Pair(Entity):
    def __init__(self, object_id):
        super().__init__(object_id)


class Bot(Entity):
    def __init__(self, object_id: str, name: str, exchange: str, strategy: Strategy, positions: list):
        super().__init__(object_id)
        self.exchange = exchange
        self.strategy = strategy
        self.positions = positions
        if name:
            self.name = name
        else:
            self._set_name()

    def __hash__(self):
        return hash((self.name, self.exchange, self.strategy, self.positions))

    def __eq__(self, other):
        return (self.name, self.exchange, self.strategy, self.positions
                ) == (other.name, other.exchange, other.strategy, other.positions)

    def _set_name(self):
        self.name = 'bot_' + str((len(Structure.bots_map) + 1))

    def get_name(self):
        return self.name
