import datetime
import re
from dataclasses import dataclass
from typing import Literal

import dateparser
import httpx
import pytz
from gazpacho import Soup

tz = pytz.timezone("Europe/Brussels")


class MangaNotFound(Exception):
    def __init__(self, name: str):
        self.name = name

    def __str__(self) -> str:
        return f"Manga named '{self.name}' not found."


@dataclass
class MangaChapter:
    num: str
    timestamp: datetime
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
            timestamp = dateparser.parse(e.find("i").text)
            num = re.sub(r"Chapter ", "", e.find("a").text)
            results.append(
                MangaChapter(
                    num=num,
                    timestamp=timestamp.astimezone(tz),
                    url=e.find("a").attrs["href"],
                )
            )

        return results


class MyNotifierClient(httpx.AsyncClient):
    def __init__(
        self, api_key: str, base_url: str = "https://api.mynotifier.app", **kwargs
    ):
        self.api_key = api_key
        super().__init__(base_url=base_url, **kwargs)

    async def push_notif(
        self,
        message: str,
        description: str,
        level: Literal["info", "warning", "error", "success"] = "info",
    ) -> None:
        data = {
            "apiKey": self.api_key,
            "message": message,
            "description": description,
            "type": level,
        }
        response = await self.post("", data=data)
        response.raise_for_status()
