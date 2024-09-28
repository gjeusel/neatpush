import enum

import bucketstore
import orjson
import structlog
from pydantic import BaseModel, validator

from neatpush import scraping
from neatpush.config import CFG
from neatpush.scraping import MangaChapter

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


def _get_s3_bucket() -> bucketstore.S3Bucket:
    bucketstore.login(
        access_key_id=CFG.CLOUD_ACCESS_KEY,
        secret_access_key=CFG.CLOUD_SECRET_KEY.get_secret_value(),
        region=CFG.CLOUD_REGION_NAME,
        endpoint_url=CFG.BUCKET_ENDPOINT_URL,
    )
    return bucketstore.get(CFG.BUCKET_NAME)


def retrieve_cached_mangas(bucket: bucketstore.S3Bucket) -> list[Manga]:
    raw = orjson.loads(bucket.get(CFG.BUCKET_KEY))
    return [Manga(**e) for e in raw]


def save_cached_mangas(bucket: bucketstore.S3Bucket, *, mangas: list[Manga]) -> None:
    bucket[CFG.BUCKET_KEY] = orjson.dumps([m.dict() for m in mangas])


def get_new_chapters(
    map_manga_source: dict[MangaSource, list[str]] | None = None,
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

    bucket = _get_s3_bucket()
    mangas = retrieve_cached_mangas(bucket)
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

    save_cached_mangas(bucket, mangas=updated_mangas)

    return to_notify_map
