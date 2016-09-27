"""
State module contains utilities for determining the agent's state
(especially during startup).
"""
import json
import logging
import multiprocessing
import platform

from halti_agent import settings, comms

logger = logging.getLogger('halti-agent')


def load_persisted_state():
    """Load state from STATE_FILE or return the DEFAULT_STATE."""
    with open(settings.STATE_FILE, 'r') as state_file:
        return json.load(state_file)


def persist_state(state):
    """Persist state into STATE_FILE."""
    with open(settings.STATE_FILE, 'w') as state_file:
        json.dump(state, state_file)


def load_state(container_client):
    """Load state from settings.STATE_FILE or Halti Master."""
    try:
        state = load_persisted_state()
        logger.info('Loaded state from {}.'.format(settings.STATE_FILE))
    except OSError:
        logger.info('{} not available, registering with master'.format(settings.STATE_FILE))
        state = comms.register(platform_state(container_client.docker_client))
        logger.info('Registered with master at {}.'.format(settings.HALTI_SERVER_URL))
        persist_state(state)
        logger.info('State saved to {}.'.format(settings.STATE_FILE))
    return state


def platform_state(docker_client):
    """Return the current platform's state as a dict.

    The resulting dict is JSON serialisable and can be sent
    to Halti Master.
    """
    return {
        'info': docker_client.info(),
        'system': {
            'cpus': multiprocessing.cpu_count(),
            'system': platform.system(),
            'system_version': platform.version(),
            'hostname': platform.node()
        },
        'docker_client': docker_client.version()
    }
