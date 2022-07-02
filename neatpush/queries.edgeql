# name: manga_chapters_upsert
WITH
    name := <str>$name,
    chapters := <json>$chapters,
FOR item IN json_array_unpack(chapters) union (
    INSERT MangaChapter {
        num := <str>item['num'],
        timestamp := <datetime>item['timestamp'],
        url := <str>item['url'],
        manga := (SELECT Manga FILTER .name = name)
    }
    UNLESS CONFLICT ON .url
);
