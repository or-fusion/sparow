import logging

# Add a 'VERBOSE' logging level
logging.VERBOSE = logging.INFO - 1
logging.addLevelName(logging.VERBOSE, "VERBOSE")


#  Add a convenience method to the Logger class
def verbose(self, message, *args, **kws):
    if self.isEnabledFor(logging.VERBOSE):
        self._log(logging.VERBOSE, message, args, **kws)


logging.Logger.verbose = verbose


class _PrefixFilter(logging.Filter):
    """
    Adds the 'sparow_prefix' attribute, which is included in the log format,
    to each log record.  This is used e.g. to identify the MPI rank that
    generated a log message.
    """

    prefix = ""

    def filter(self, record):
        record.sparow_prefix = self.prefix
        return True


logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
_prefix_filter = _PrefixFilter()
handler.addFilter(_prefix_filter)
formatter = logging.Formatter("%(sparow_prefix)s%(levelname)s - %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)


def use_debugging_formatter():
    formatter = logging.Formatter(
        "%(asctime)s - %(sparow_prefix)s%(levelname)s - %(message)s"
    )
    handler.setFormatter(formatter)


def set_log_prefix(prefix):
    """
    Set a prefix for all log messages (e.g. "[rank 3] ").  The default is the
    empty string.
    """
    _prefix_filter.prefix = prefix
