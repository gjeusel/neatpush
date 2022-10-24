"""NeatPush - wanted notificiations and nothing else."""

from importlib import metadata

__version__ = metadata.version("neatpush")


import warnings

# TODO: remove once https://github.com/scrapinghub/dateparser/issues/1013 is tagged
# Ignore dateparser warnings regarding pytz
warnings.filterwarnings(
    "ignore",
    message="The localize method is no longer necessary, as this time zone supports the fold attribute",  # noqa
)
