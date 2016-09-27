from halti_agent import settings

__version__ = '0.1.0'
__author__ = 'Emblica, Inc.'
__author_email__ = 'hello@emblica.fi'
__license__ = 'EMBLICA HALTI SHARED SOURCE LICENSE'
__copyright__ = 'Copyright (c) 2015 Emblica, Inc.'


def halti_agent_info():
    """Return useful information and settings of this Halti-Agent instance."""
    return {
        'agent_version': __version__,
        'port': settings.PORT_BIND_IP,
        'halti_master': settings.HALTI_SERVER_URL
    }
