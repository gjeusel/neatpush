import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import dateparser
import httpx
from gazpacho import Soup


@dataclass
class NMReleases:
    chapter: str
    timestamp: datetime
    url: str


class NeatMangaClient(httpx.Client):
    def __init__(self, base_url: str = "https://neatmanga.com"):
        super().__init__(base_url=base_url)

    def get_latest_releases(self, manga: str) -> list[Any]:
        endpoint = f"/manga/{manga}/ajax/chapters/"
        resp = self.post(endpoint)
        resp.raise_for_status()
        soup = Soup(resp.text)

        raw = soup.find("li", attrs={"class": "wp-manga-chapter"})

        results: list[NMReleases] = []
        for e in raw:
            timestamp = dateparser.parse(e.find("i").text)
            chapter = re.sub(r"Chapter ", "", e.find("a").text)
            results.append(
                NMReleases(
                    chapter=chapter, timestamp=timestamp, url=e.find("a").attrs["href"]
                )
            )

        return results
