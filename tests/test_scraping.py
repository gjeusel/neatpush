import pytest

from neatpush import scraping


@pytest.mark.parametrize(
    "name, scraping_fn, nchapters_expected",
    (
        ("overgeared", scraping.scrap_neatmanga, 160),
        ("jujutsu-kaisen", scraping.scrap_mangapill, 212),
        ("tales-of-demons-and-gods", scraping.scrap_toonily, 854),
    ),
)
def test_it_can_retrieve_chapters(vcr, name, scraping_fn, nchapters_expected):
    with vcr.use_cassette(f"scrap_{name}.yaml"):
        results = scraping_fn(name)

    assert len(results) == nchapters_expected
