from __future__ import annotations

from datetime import datetime

from sqlmodel import Field, Relationship, SQLModel


class Manga(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str
    chapters: list[MangaChapter] = Relationship(back_populates="manga")


class MangaChapter(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    num: str
    url: str
    notify: bool = Field(default=False)
    timestamp: datetime = Field(default=datetime.utcnow)

    manga_id: int | None = Field(default=None, foreign_key="manga.id")
    manga: Manga | None = Relationship(back_populates="chapters")
