import pytest

from neatpush import scraping


@pytest.mark.parametrize(
    "name, scraping_fn, nchapters_expected",
    (
        ("overgeared", scraping.scrap_neatmanga, 161),
        ("jujutsu-kaisen", scraping.scrap_mangapill, 213),
        ("tales-of-demons-and-gods", scraping.scrap_toonily, 1356),
    ),
)
def test_it_can_retrieve_chapters(vcr, name, scraping_fn, nchapters_expected):
    with vcr.use_cassette(f"scrap_{name}.yaml"):
        results = scraping_fn(name)

    assert len(results) == nchapters_expected
