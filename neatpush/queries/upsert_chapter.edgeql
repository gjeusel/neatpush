# WITH
#     name := <str>$name,
#     chapters := <json>$chapters,
# FOR item IN json_array_unpack(chapters) union (
#     INSERT MangaChapter {
#         num := <str>item['num'],
#         timestamp := <datetime>item['timestamp'],
#         url := <str>item['url'],
#         manga := (SELECT Manga FILTER .name = name)
#     }
#     UNLESS CONFLICT ON .url
# );

INSERT MangaChapter {
  num := <str>$num,
  timestamp := <datetime>$timestamp,
  url := <str>$url,
  manga := (Select Manga FILTER .name = <str>$manga_name),
}
