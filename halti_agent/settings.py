"""
Settings an related helpers.

We use dotenv which means that the project root has a file called `.env`
that is read and its content loaded as environment variables with `load_dotenv`.

This allows specifying envs (for `get_env`) in a file rather than as actual
environment variables. This is useful for development, however, the file
should always be empty in production.
"""

import logging
from logging.config import dictConfig as LOGGING_CONFIG
import os
from os.path import dirname
from docker.utils import kwargs_from_env


def get_env(env, default=None):
    """os.environ wrapper with boolean conversions."""
    val = os.environ.get(env, default)
    if val in ['True', 'true']:
        val = True
    if val in ['False', 'false']:
        val = False
    return val


def load_dotenv():
    """Load environment variables from .env"""
    with open(os.path.join(BASE_DIR, '.env')) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#') or '=' not in line:
                continue

            k, v = line.split('=', 1)
            k, v = k.strip(), v.strip()

            if len(v) > 0 and v[0] == v[len(v) - 1] == '"':
                v = v[1:-1]
            os.environ[k] = v


BASE_DIR = dirname(dirname(__file__))
load_dotenv()

PORT_BIND_IP = get_env('PORT_BIND_IP', '127.0.0.1')
HALTI_SERVER_URL = get_env('HALTI_SERVER', 'http://localhost:4040')
ALLOW_INSECURE_REGISTRY = get_env('ALLOW_INSEC_REGISTRY', False)

CAPABILITIES = get_env('CAPABILITIES', '').split(',')

STATE_FILE = 'state.json'

DOCKER_OPTIONS = options = {
    **kwargs_from_env(),
    'version': 'auto'
}


LOG_LEVEL_MAP = {
    'DEBUG': logging.DEBUG,
    'INFO': logging.INFO,
    'WARNING': logging.WARNING,
    'ERROR': logging.ERROR,
}

LOG_LEVEL = LOG_LEVEL_MAP.get(get_env('LOG_LEVEL'), 'INFO')

LOGGING_CONFIG({
    'version': 1,
    'formatters': {
        'f': {'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s'}
    },
    'handlers': {
        'h': {'class': 'logging.StreamHandler',
              'formatter': 'f',
              'level': LOG_LEVEL}
    },
    'root': {
        'handlers': ['h'],
        'level': LOG_LEVEL,
    },
})
