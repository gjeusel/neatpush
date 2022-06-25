import pytest

from neatpush.neatmanga import NeatMangaClient

from . import VCR_DIR


@pytest.fixture
def client() -> NeatMangaClient:
    return NeatMangaClient()


class TestNeatMangaClient:
    def test_it_can_retrieve_latest_releases(self, client, vcr):
        manga = "berserk"
        with vcr.use_cassette(f"neatmanga_latest_releases_{manga}"):
            results = client.get_latest_releases(manga)

        assert len(results) == 401
