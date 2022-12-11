import traceback
from datetime import datetime, timedelta
from types import SimpleNamespace


def name_cat_mapping(config: SimpleNamespace) -> dict:
    return {r.name: r.category for r in config.rules}


def get_stacktrace(ex: Exception) -> str:
    """Extracts a stacktrace string from an `Exception` object."""
    return "".join(traceback.TracebackException.from_exception(ex).format())


def get_rowkey_datestamp() -> int:
    """Gets the number of seconds from now until 12/31/2999."""
    return convert_date_rowkey(datetime.utcnow())


def convert_date_rowkey(date: datetime) -> int:
    """Gets the number of seconds from the specified `date` until 12/31/2999."""
    return int((max_datetime() - date).total_seconds() * 10)


def get_datetime_from_rowkey_secs(seconds: int) -> datetime:
    """Gets a `datetime` object representing the number of seconods until 12/31/2999."""
    return (max_datetime() - timedelta(seconds=seconds / 10))


def max_datetime() -> datetime:
    return datetime(2999, 12, 31, 0, 0, 0, 0)
