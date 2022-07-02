import uuid
from pathlib import Path
from typing import Protocol, cast

import edgedb
import edgeql_queries


class BaseObj(Protocol):
    id: uuid.UUID


class Queries:
    async def manga_chapters_upsert(
        self,
        executor: edgedb.AsyncIOExecutor,
        name: str,
        chapters: str,
    ) -> set[BaseObj]:
        ...


queries_path = Path(__file__).parent / "queries.edgeql"
queries = cast(Queries, edgeql_queries.from_path(queries_path.as_posix()))
