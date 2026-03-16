from copy import deepcopy

from bson import ObjectId


class InsertOneResult:
    def __init__(self, inserted_id):
        self.inserted_id = inserted_id


class UpdateResult:
    def __init__(self, matched_count=0, modified_count=0):
        self.matched_count = matched_count
        self.modified_count = modified_count


class DeleteResult:
    def __init__(self, deleted_count=0):
        self.deleted_count = deleted_count


class FakeCursor:
    def __init__(self, documents):
        self._documents = [deepcopy(document) for document in documents]

    async def to_list(self, length=None):
        if length is None:
            return deepcopy(self._documents)
        return deepcopy(self._documents[:length])


class FakeCollection:
    def __init__(self):
        self._documents = []

    async def insert_one(self, document):
        stored = deepcopy(document)
        stored.setdefault("_id", ObjectId())
        self._documents.append(stored)
        return InsertOneResult(stored["_id"])

    async def find_one(self, query):
        for document in self._documents:
            if _matches(document, query):
                return deepcopy(document)
        return None

    def find(self, query):
        matches = [document for document in self._documents if _matches(document, query)]
        return FakeCursor(matches)

    async def update_one(self, query, update):
        for document in self._documents:
            if _matches(document, query):
                _apply_update(document, update)
                return UpdateResult(matched_count=1, modified_count=1)
        return UpdateResult()

    async def delete_many(self, query):
        before = len(self._documents)
        if not query:
            self._documents.clear()
            return DeleteResult(deleted_count=before)

        self._documents = [
            document for document in self._documents if not _matches(document, query)
        ]
        return DeleteResult(deleted_count=before - len(self._documents))


class FakeDatabase:
    def __init__(self):
        self._collections = {
            "users": FakeCollection(),
            "sessions": FakeCollection(),
            "enrollments": FakeCollection(),
            "ratings": FakeCollection(),
        }

    def __getitem__(self, collection_name):
        if collection_name not in self._collections:
            self._collections[collection_name] = FakeCollection()
        return self._collections[collection_name]

    def __getattr__(self, collection_name):
        return self[collection_name]

    async def list_collection_names(self):
        return list(self._collections.keys())


class FakeMongoClient:
    def __init__(self):
        self._databases = {}

    def __getitem__(self, database_name):
        if database_name not in self._databases:
            self._databases[database_name] = FakeDatabase()
        return self._databases[database_name]

    def close(self):
        return None


def _matches(document, query):
    for key, expected in query.items():
        if key == "$or":
            return any(_matches(document, branch) for branch in expected)

        actual = document.get(key)

        if isinstance(expected, dict):
            if "$ne" in expected:
                if actual == expected["$ne"]:
                    return False
                continue
            return False

        if actual != expected:
            return False

    return True


def _apply_update(document, update):
    for operator, values in update.items():
        if operator == "$set":
            for key, value in values.items():
                document[key] = value
            continue

        if operator == "$inc":
            for key, value in values.items():
                document[key] = document.get(key, 0) + value
            continue

        raise NotImplementedError(f"Unsupported update operator: {operator}")
