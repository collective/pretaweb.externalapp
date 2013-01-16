import sys
import logging


LOGGER = logging.getLogger('pretaweb.externalapp')

def logException(msg, context=None, logger=LOGGER):
    logger.exception(msg)
    if context is not None:
        error_log = getattr(context, 'error_log', None)
        if error_log is not None:
            error_log.raising(sys.exc_info())
