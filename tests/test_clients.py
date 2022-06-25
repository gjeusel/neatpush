import pytest

from neatpush import clients


@pytest.fixture
def manga_client() -> clients.MangaClient:
    return clients.MangaClient()


class TestMangaClient:
    async def test_it_can_retrieve_latest_releases(self, vcr, manga_client):
        manga = "berserk"
        with vcr.use_cassette(f"neatmanga_latest_releases_{manga}.yaml"):
            results = await manga_client.get_neatmanga_latest_releases(manga)

        assert len(results) == 401
