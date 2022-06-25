import re
from dataclasses import dataclass

import dateparser
import httpx
import pandas as pd
from gazpacho import Soup


class MangaNotFound(Exception):
    def __init__(self, name: str):
        self.name = name

    def __str__(self) -> str:
        return f"Manga named '{self.name}' not found."


@dataclass
class MangaChapter:
    num: str
    timestamp: pd.Timestamp
    url: str


class MangaClient(httpx.AsyncClient):
    async def get_neatmanga_latest_releases(self, manga: str) -> list[MangaChapter]:
        url = f"https://neatmanga.com/manga/{manga}/ajax/chapters"
        resp = await self.post(url)

        if resp.status_code == 404:
            raise MangaNotFound(manga)

        resp.raise_for_status()
        soup = Soup(resp.text)

        raw = soup.find("li", attrs={"class": "wp-manga-chapter"})

        results: list[MangaChapter] = []
        for e in raw:
            timestamp = pd.Timestamp(dateparser.parse(e.find("i").text))
            chapter = re.sub(r"Chapter ", "", e.find("a").text)
            results.append(
                MangaChapter(
                    num=chapter,
                    timestamp=timestamp.tz_localize("CET"),
                    url=e.find("a").attrs["href"],
                )
            )

        return results
