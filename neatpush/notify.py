from typing import Any

import boto3

from neatpush.scraping import MangaChapter

from .config import CFG


def format_new_chapters(map_new_chapters: dict[str, list[MangaChapter]]) -> str:
    pieces = []
    for name, chapters in map_new_chapters.items():
        if len(chapters) == 0:
            continue

        pieces.append(f"Found {len(chapters)} new chapters for {name}")
        for chapter in chapters:
            pieces.append(f"- {chapter.num}: {chapter.url}")

    return "\n".join(pieces)


def send_sms(message: str) -> dict[str, Any]:
    session = boto3.Session(
        aws_access_key_id=CFG.AWS_ACCESS_KEY,
        aws_secret_access_key=CFG.AWS_SECRET_KEY.get_secret_value(),
        region_name=CFG.AWS_REGION_NAME,
    )
    client = session.client("sns")  # Simple Notifications Service

    resp = client.publish(Message=message, TopicArn=CFG.AWS_SNS_TOPIC)
    return resp
