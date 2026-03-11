from backend.domain.input_source import InputSource

class InputSourceRepository:
    def __init__(self):
        self._items: list[InputSource] = []
        self._next_id = 1

    def add(self, source: InputSource):
        source.source_id = self._next_id
        self._items.append(source)
        self._next_id +=1

    def list(self):
        return self._items.copy()
    
    def get(self, id: int):
        for i in range(len(self._items)):
            if self._items[i].source_id == id:
                return self._items[i]
        return None

source_repo = InputSourceRepository()

