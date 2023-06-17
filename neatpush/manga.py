import enum
import tempfile
from typing import Any

import boto3
import orjson
import structlog
from botocore.exceptions import ClientError as BotoClientError
from pydantic import BaseModel, validator

from neatpush.config import CFG

from . import scraping
from .scraping import MangaChapter

logger = structlog.getLogger(__name__)


class MangaSource(str, enum.Enum):
    neatmanga = "neatmanga"
    mangapill = "mangapill"
    toonily = "toonily"


class Manga(BaseModel):
    name: str
    source: MangaSource
    chapters: list[MangaChapter]

    @property
    def n_chapters(self) -> int:
        return len(self.chapters)

    @validator("chapters")
    def _sort_chapters(cls, values: list[MangaChapter]) -> list[MangaChapter]:
        return sorted(values, key=lambda x: x.num)

    def __repr__(self) -> str:
        return f"<Manga {self.name} - {self.source}> #{self.n_chapters} chapters"

    __str__ = __repr__


def scrap_manga(cache: Manga) -> list[MangaChapter]:
    """Scrap chapters for a given manga, and return uncommunicated chapters."""
    return []


DEFAULT_BUCKET_KEY = "neatpush.json"


def _get_s3_client() -> Any:
    session = boto3.Session(
        aws_access_key_id=CFG.MY_SCW_ACCESS_KEY,
        aws_secret_access_key=CFG.MY_SCW_SECRET_KEY.get_secret_value(),
        region_name=CFG.MY_SCW_REGION_NAME,
    )

    return session.client(
        "s3",
        endpoint_url=CFG.MY_SCW_BUCKET_ENDPOINT_URL,
    )


def retrieve_cached_mangas(s3: Any, *, path: str = DEFAULT_BUCKET_KEY) -> list[Manga]:
    tmp_filepath = tempfile.gettempdir() + "/tmp.json"

    try:
        s3.download_file(Bucket=CFG.MY_SCW_BUCKET, Key=path, Filename=tmp_filepath)
    except BotoClientError as err:
        if "Not Found" in str(err):
            return []
        else:
            raise

    with open(tmp_filepath) as f:
        content = f.read()
        raw = orjson.loads(content)

    mangas = [Manga(**e) for e in raw]
    return mangas


def save_cached_mangas(
    s3: Any, *, mangas: list[Manga], path: str = DEFAULT_BUCKET_KEY
) -> None:
    contents = orjson.dumps([m.dict() for m in mangas])
    s3.put_object(Bucket=CFG.MY_SCW_BUCKET, Key=path, Body=contents)


def get_new_chapters(
    map_manga_source: dict[MangaSource, list[str]] | None = None
) -> dict[str, list[MangaChapter]]:
    map_manga_source = map_manga_source or {
        MangaSource.mangapill: CFG.MANGAPILL,
        MangaSource.neatmanga: CFG.NEATMANGA,
        MangaSource.toonily: CFG.TOONILY,
    }

    logger.debug("checking-sources", **map_manga_source)

    map_source_fn = {
        MangaSource.neatmanga: scraping.scrap_neatmanga,
        MangaSource.mangapill: scraping.scrap_mangapill,
        MangaSource.toonily: scraping.scrap_toonily,
    }

    s3 = _get_s3_client()
    mangas = retrieve_cached_mangas(s3)
    map_name_cache = {m.name: m for m in mangas}

    updated_mangas: list[Manga] = []
    to_notify_map: dict[str, list[MangaChapter]] = {}

    for source, names in map_manga_source.items():
        scrap_fn = map_source_fn[source]
        if scrap_fn is None:
            continue

        log = logger.bind(source=source.value)

        for name in names:
            log = log.bind(name=name)

            log.debug("checking-start")
            try:
                chapters = scrap_fn(name)
            except Exception:
                log.exception("failed-scrap")
                continue

            if name not in map_name_cache:
                updated_mangas.append(
                    Manga(name=name, source=source, chapters=chapters)
                )
                log.info("first-time", nchapters=len(chapters))
                continue

            manga = map_name_cache[name]
            new_chapters = sorted(
                set(chapters) - set(manga.chapters), key=lambda x: x.num
            )

            if not new_chapters:
                log.debug("nothing-new")
            else:
                log.info("new-chapters", nums=[c.num for c in new_chapters])
                to_notify_map[name] = new_chapters

            updated_mangas.append(
                Manga(
                    name=name,
                    source=source,
                    chapters=list(set(manga.chapters) | set(chapters)),
                )
            )

    save_cached_mangas(s3, mangas=updated_mangas)

    return to_notify_map
