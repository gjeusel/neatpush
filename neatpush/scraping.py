import re
import warnings
from dataclasses import dataclass, field
from datetime import datetime

import bs4
import dateparser
import httpx
import pytz
import structlog

Soup = bs4.BeautifulSoup

warnings.filterwarnings(action="ignore", category=bs4.GuessedAtParserWarning)

tz = pytz.timezone("Europe/Brussels")

logger = structlog.getLogger(__name__)


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
    url: str
    num: float = field(compare=False)
    timestamp: datetime = field(compare=False)

    def __repr__(self) -> str:
        ts = self.timestamp.strftime("%Y-%m-%d")
        return f"<MangaChapter {self.num}> {ts}"

    __str__ = __repr__


PATTERN_NUM = re.compile(r"\d+\.?\d*")


def scrap_neatmanga(name: str) -> set[MangaChapter]:
    url = f"https://neatmanga.com/manga/{name}/ajax/chapters"
    resp = httpx.post(url, follow_redirects=True)

    if resp.status_code == 404:
        raise MangaNotFound(name)
    elif not resp.is_success:
        raise ScrapingError(f"Failed to scrap {name}: {resp.text}")

    resp.raise_for_status()
    soup = Soup(resp.text)

    raw = soup.find_all("li", attrs={"class": "wp-manga-chapter"})

    results: list[MangaChapter] = []
    for e in raw:
        timestamp = dateparser.parse(e.find("i").text)
        assert timestamp, f"Could not find timestamp for {name} on {e}"

        a = e.find("a")

        match = PATTERN_NUM.search(a.text)
        if match:
            num = match[0]
        else:
            continue

        results.append(
            MangaChapter(
                num=float(num),
                timestamp=timestamp.astimezone(tz),
                url=a.attrs["href"],
            )
        )

    return set(results)


def scrap_mangapill(name: str) -> set[MangaChapter]:
    base_url = "https://mangapill.com"
    search_url = f"{base_url}/quick-search"
    search_resp = httpx.get(search_url, params={"q": name})

    search_soup = Soup(search_resp.text)
    endpoint = search_soup.find("a").attrs["href"]  # type: ignore

    url = f"{base_url}{endpoint}"
    resp = httpx.get(url)

    soup = Soup(resp.text)
    pattern = re.compile("^/chapters")
    raw = soup.find_all("a", attrs={"href": pattern})

    chapters: list[MangaChapter] = []
    for e in raw:
        endpoint = e.attrs["href"]
        url = f"{base_url}{endpoint}"

        match = PATTERN_NUM.search(e.text)
        if match:
            num = match[0]
        else:
            continue

        chapters.append(
            MangaChapter(
                url=url,
                num=float(num),
                timestamp=datetime.utcnow(),
            )
        )

    return set(chapters)


def scrap_toonily(name: str) -> set[MangaChapter]:
    url = f"https://toonily.net/manga/{name}/"
    resp = httpx.get(url)

    soup = Soup(resp.text)
    raw = soup.find_all("li", attrs={"class": "wp-manga-chapter"})

    pattern = re.compile(f"^{url}")
    results: list[MangaChapter] = []
    for e in raw:
        a = e.find("a", attrs={"href": pattern})
        href = a.attrs["href"]

        match = PATTERN_NUM.search(a.text)
        if match:
            num = match[0]
        else:
            continue

        if e.find("i"):
            soup_timestamp = e.find("i").text
        else:
            soup_timestamp = e.find_all("a")[-1].attrs["title"]

        timestamp = dateparser.parse(soup_timestamp)
        assert timestamp, f"Failed to find timestamp for {name} on toonily"

        results.append(
            MangaChapter(
                num=float(num),
                timestamp=timestamp.astimezone(tz),
                url=href,
            )
        )

    assert results, f"Found no chapters for {name}"

    return set(results)
