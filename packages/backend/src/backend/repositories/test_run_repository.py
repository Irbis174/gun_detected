from backend.domain.test_run import TestRun

class TestRunRepository:
    def __init__(self):
        self._items: list[TestRun] = []
        self._next_id = 1

    def add(self, test_run: TestRun):
        test_run.test_run_id = self._next_id
        self._items.append(test_run)
        self._next_id += 1

    def list(self):
        return self._items.copy()

    def get(self, id: int):
        for i in range(len(self._items)):
            if self._items[i].test_run_id == id:
                return self._items[i]
        return None

test_run_repo = TestRunRepository()
