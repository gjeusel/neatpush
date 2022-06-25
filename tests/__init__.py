import logging
from pathlib import Path

vcr_log = logging.getLogger("vcr")
vcr_log.setLevel(logging.WARNING)


DATA_TEST_DIR = Path(__file__).parent / "data"
VCR_DIR = DATA_TEST_DIR / "vcr_cassettes"
