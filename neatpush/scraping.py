import datetime
import re
from dataclasses import dataclass, field
from typing import Any

import dateparser
import httpx
import pytz
from gazpacho import Soup

tz = pytz.timezone("Europe/Brussels")


class ScrappingError(Exception):
    pass


class MangaNotFound(ScrappingError):
    def __init__(self, name: str):
        self.name = name
        super().__init__(name)

    def __str__(self) -> str:
        return f"Manga named '{self.name}' not found."


@dataclass(repr=False, frozen=True)
class MangaChapter:
    url: str
    num: str
    timestamp: datetime.datetime = field(compare=False)  # __hash__ is based on __eq__

    def __repr__(self) -> str:
        ts = self.timestamp.strftime("%Y-%m-%d")
        return f"<MangaChapter {self.num}> {ts}"


def scrap_neatmanga(name: str) -> list[MangaChapter]:
    url = f"https://neatmanga.com/manga/{name}/ajax/chapters"
    resp = httpx.post(url, follow_redirects=True)

    if resp.status_code == 404:
        raise MangaNotFound(name)
    elif not resp.is_success:
        raise ScrappingError(f"Failed to scrap {name}: {resp.text}")

    resp.raise_for_status()
    soup = Soup(resp.text)

    raw = soup.find("li", attrs={"class": "wp-manga-chapter"})

    if not isinstance(raw, list):
        raise ValueError(f"Failed to parse html for {name}.")

    results: list[MangaChapter] = []
    for e in raw:
        timestamp = dateparser.parse(e.find("i").text)  # type: ignore
        if not timestamp:
            raise ValueError(f"Could not find timestamp for {name} on {e}")
        num = re.sub(r"Chapter ", "", e.find("a").text)  # type: ignore
        results.append(
            MangaChapter(
                num=num,
                timestamp=timestamp.astimezone(tz),
                url=e.find("a").attrs["href"],  # type: ignore
            )
        )

    results = sorted(set(results), key=lambda x: x.timestamp)
    return results
