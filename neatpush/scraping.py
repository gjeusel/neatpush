import re
from dataclasses import dataclass, field
from datetime import datetime

import dateparser
import httpx
import pytz
from gazpacho import Soup

tz = pytz.timezone("Europe/Brussels")


class ScrapingError(Exception):
    pass


class MangaNotFound(ScrapingError):
    def __init__(self, name: str):
        self.name = name
        super().__init__(name)

    def __str__(self) -> str:
        return f"Manga named '{self.name}' not found."


@dataclass(repr=False, frozen=True)
class MangaChapter:
    url: str = field()
    num: str
    timestamp: datetime = field(compare=False)  # __hash__ is based on __eq__

    def __repr__(self) -> str:
        ts = self.timestamp.strftime("%Y-%m-%d")
        return f"<MangaChapter {self.num}> {ts}"


def scrap_neatmanga(name: str) -> list[MangaChapter]:
    url = f"https://neatmanga.com/manga/{name}/ajax/chapters"
    resp = httpx.post(url, follow_redirects=True)

    if resp.status_code == 404:
        raise MangaNotFound(name)
    elif not resp.is_success:
        raise ScrapingError(f"Failed to scrap {name}: {resp.text}")

    resp.raise_for_status()
    soup = Soup(resp.text)

    raw = soup.find("li", attrs={"class": "wp-manga-chapter"})
    assert isinstance(raw, list), f"Failed to parse html for {name}."

    results: list[MangaChapter] = []
    for e in raw:
        timestamp = dateparser.parse(e.find("i").text)  # type: ignore
        assert timestamp, f"Could not find timestamp for {name} on {e}"
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


def scrap_mangapill(name: str) -> list[MangaChapter]:
    base_url = "https://mangapill.com"
    search_url = f"{base_url}/quick-search"
    search_resp = httpx.get(search_url, params={"q": name})

    search_soup = Soup(search_resp.text)
    soup_best_match = search_soup.find("a", attrs={"href": "/manga"}, mode="first")

    assert isinstance(soup_best_match, Soup)
    assert soup_best_match.attrs
    endpoint = soup_best_match.attrs["href"]

    url = f"{base_url}{endpoint}"
    resp = httpx.get(url)

    soup = Soup(resp.text)
    raw = soup.find("a", attrs={"href": "/chapters"})
    assert isinstance(raw, list)

    chapters: list[MangaChapter] = []
    for e in raw:
        assert e.attrs
        endpoint = e.attrs["href"]
        url = f"{base_url}{endpoint}"
        num = e.text.split("Chapter ")[-1].strip()
        chapters.append(MangaChapter(url=url, num=num, timestamp=datetime.utcnow()))

    return chapters


def scrap_toonily(name: str) -> list[MangaChapter]:
    url = f"https://toonily.net/manga/{name}/"
    resp = httpx.get(url)

    soup = Soup(resp.text)
    raw = soup.find("li", attrs={"class": "wp-manga-chapter"})
    assert isinstance(raw, list)

    results: list[MangaChapter] = []
    for e in raw:
        a = e.find("a", attrs={"href": url}, mode="first")
        if not isinstance(a, Soup):
            continue

        assert a.attrs
        href = a.attrs["href"]
        num = a.text.split("chapter-")[-1].strip()

        if e.find("i"):
            soup_timestamp = e.find("i", mode="first").text  # type: ignore
        else:
            soup_timestamp = e.find("a", attrs={"title": ""}, mode="first").attrs["title"]  # type: ignore

        timestamp = dateparser.parse(soup_timestamp)
        assert timestamp, f"Failed to find timestamp for {name} on toonily"

        results.append(
            MangaChapter(
                num=num,
                timestamp=timestamp.astimezone(tz),
                url=href,
            )
        )

    assert results, f"Found no chapters for {name}"

    return results
