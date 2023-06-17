from neatpush.manga import MangaSource, get_new_chapters


def test_get_new_chapters(mocker, vcr):
    mocker.patch("neatpush.manga._get_s3_bucket")

    mocker.patch("neatpush.manga.retrieve_cached_mangas", return_value=[])
    mocked_save_cached_mangas = mocker.patch("neatpush.manga.save_cached_mangas")

    map_manga_source = {MangaSource.mangapill: ["chainsaw-man", "one-punch-man"]}
    cassette = "orchestration.yaml"
    with vcr.use_cassette(cassette):
        result = get_new_chapters(map_manga_source)

    assert not result
    mangas = mocked_save_cached_mangas.call_args.kwargs["mangas"]
    assert len(mangas) == 2

    map_name_manga = {manga.name: manga for manga in mangas}
    assert map_name_manga["chainsaw-man"].n_chapters == 132
    assert map_name_manga["one-punch-man"].n_chapters == 235

    mocker.patch("neatpush.manga.retrieve_cached_mangas", return_value=mangas)
    with vcr.use_cassette(cassette):
        result = get_new_chapters(map_manga_source)
    assert not result  # no new chapter

    chapter = map_name_manga["chainsaw-man"].chapters.pop()
    mocker.patch("neatpush.manga.retrieve_cached_mangas", return_value=mangas)
    with vcr.use_cassette(cassette):
        result = get_new_chapters(map_manga_source)

    assert len(result["chainsaw-man"]) == 1
    assert result["chainsaw-man"][0].num == chapter.num
