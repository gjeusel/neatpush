import enum
import tempfile
from dataclasses import dataclass
from typing import Any, Sequence

import boto3
import orjson
import structlog
from boto3.exceptions import S3TransferFailedError
from botocore.exceptions import ClientError as BotoClientError
from pydantic import BaseModel, validator

from neatpush.config import CFG

from . import scraping
from .scraping import MangaChapter

logger = structlog.getLogger(__name__)

# https://neatmanga.com/manga/overgeared/2020/

# https://toonily.net/manga/tales-of-demons-and-gods/

# https://mangapill.com/manga/5284/omniscient-reader
# https://mangapill.com/manga/2085/jujutsu-kaisen
# https://mangapill.com/manga/2/one-piece
# https://mangapill.com/manga/723/chainsaw-man
# https://mangapill.com/manga/3262/one-punch-man


class MangaSource(str, enum.Enum):
    neatmanga = "neatmanga"
    mangapill = "mangapill"
    toonily = "toonily"


class Manga(BaseModel):
    name: str
    source: MangaSource
    chapters: list[MangaChapter]

    @validator("chapters")
    def _sort_chapters(cls, values: list[MangaChapter]) -> list[MangaChapter]:
        values.sort(key=lambda x: x.timestamp)
        return values

    def __repr__(self) -> str:
        return f"<Manga {self.name} - {self.source}>"


def scrap_manga(cache: Manga) -> list[MangaChapter]:
    """Scrap chapters for a given manga, and return uncommunicated chapters."""
    return []


DEFAULT_BUCKET_KEY = "neatpush.json"


def _get_s3_client() -> Any:
    session = boto3.Session(
        aws_access_key_id=CFG.SCW_ACCESS_KEY,
        aws_secret_access_key=CFG.SCW_SECRET_KEY.get_secret_value(),
        region_name=CFG.SCW_REGION_NAME,
    )

    return session.client(
        "s3",
        endpoint_url=CFG.SCW_BUCKET_ENDPOINT_URL,
    )


def retrieve_cached_mangas(s3: Any, *, path: str = DEFAULT_BUCKET_KEY) -> list[Manga]:
    tmp_filepath = tempfile.gettempdir() + "/tmp.json"

    try:
        s3.download_file(Bucket=CFG.SCW_BUCKET, Key=path, Filename=tmp_filepath)
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
    s3.put_object(Bucket=CFG.SCW_BUCKET, Key=path, Body=contents)


def get_new_chapters() -> dict[str, list[MangaChapter]]:
    map_manga_source = {
        MangaSource.neatmanga: CFG.NEATMANGA,
        MangaSource.mangapill: CFG.MANGAPILL,
        MangaSource.toonily: CFG.TOONILY,
    }

    map_source_fn = {
        MangaSource.neatmanga: scraping.scrap_neatmanga,
        MangaSource.mangapill: None,
        MangaSource.toonily: None,
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

        for name in names:
            logger.info(f"Checking new chapters for {name} in {source.value}...")
            chapters = scrap_fn(name)

            if name not in map_name_cache:
                # Handle case when manga is not yet in the cache.
                # We don't want to notify anything there.
                updated_mangas.append(
                    Manga(name=name, source=source, chapters=chapters)
                )
                continue

            manga = map_name_cache[name]
            new_chapters = sorted(
                set(chapters) - set(manga.chapters), key=lambda x: x.timestamp
            )
            to_notify_map[name] = new_chapters
            updated_mangas.append(
                Manga(
                    name=name,
                    source=source,
                    chapters=set(manga.chapters) | set(chapters),
                )
            )

    save_cached_mangas(s3, mangas=updated_mangas)

    return to_notify_map
