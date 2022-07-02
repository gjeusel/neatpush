import datetime
import re
from dataclasses import dataclass
from typing import Any

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


class TwilioClient(httpx.AsyncClient):
    notify_base_url = "https://notify.twilio.com"
    api_base_url = "https://api.twilio.com"

    def __init__(
        self,
        account_sid: str,
        auth_token: str,
        service_sid: str | None = None,
        **kwargs: dict[str, Any],
    ):
        super().__init__(**kwargs, auth=(account_sid, auth_token))
        self.account_sid = account_sid
        self.service_sid = service_sid

    async def send_whatsapp_msg(
        self,
        num_to: str,
        message: str,
        num_from: str | None = None,
    ) -> dict[str, Any]:
        url = f"{self.api_base_url}/2010-04-01/Accounts/{self.account_sid}/Messages.json"  # noqa
        data = {"To": f"whatsapp:{num_to}", "Body": message}
        if num_from:
            data["From"] = f"whatsapp:{num_from}"

        resp = await self.post(url, data=data)
        resp.raise_for_status()
        return resp.json()

    async def notify(self, message: str) -> dict[str, Any]:
        url = f"{self.notify_base_url}/v1/Services/{self.service_sid}/Notifications"
        data = {"Identity": "0000001", "Body": message}

        resp = await self.post(url, data=data)
        resp.raise_for_status()
        return resp.json()
