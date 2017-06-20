"""
comms module handles communications with Halti Master.

Currently a keep-alive HTTP connection and JSON is used but we should be able to
change this to anything with minimal effort.
"""
import json
import logging
import requests

from halti_agent import settings

logger = logging.getLogger('halti-agent-comms')

s = requests.Session()
s.headers.update({'Content-Type': 'application/json',
                  'Accept': 'application/json'})

# store instance ID here so comms always has access to it
INSTANCE_ID = None


HEARTBEAT_URL = '/api/v1/instances/{}/heartbeat'
REGISTER_URL = '/api/v1/instances/register'
NOTIFY_URL = '/api/v1/instances/{}/notify'


def post_json(url, payload):
    """HTTP Post payload to given url with correct headers."""
    full_url = settings.HALTI_SERVER_URL + url
    data = json.dumps(payload)
    res_json = s.post(full_url, data=data).json()
    logger.debug('received data: {}'.format(res_json))
    return res_json


def heartbeat(payload):
    """Perform Halti Heartbeat with Halti Master."""
    return post_json(HEARTBEAT_URL.format(INSTANCE_ID), payload)


def register(payload):
    """Register this node with Halti master."""
    return post_json(REGISTER_URL, payload)


def notify_master(event, meta):
    """Notify master with an Halti Event."""
    try:
        return post_json(NOTIFY_URL.format(INSTANCE_ID), halti_event(event, meta))
    except requests.RequestException as ex:
        logger.error('could not notify master: {}'.format(ex), exc_info=True)


class Events(object):
    """Halti Event constants."""
    PULL_FAILED = 'PULL_FAILED'
    PULL_START = 'PULL_START'
    START_CONTAINER = 'START_CONTAINER'
    START_CONTAINER_FAILED = 'START_CONTAINER_FAILED'
    STOP_CONTAINER = 'STOP_CONTAINER'


def halti_event(event, meta=''):
    """event, meta => Halti Event.

    Automatically determines event_type (default is "INFO").
    """
    types = {
        'INFO': {Events.PULL_START},
        'ERROR': {Events.PULL_FAILED}
    }

    def _get_event_type(event):
        return next((t for t, evnts in types.items() if event in evnts), 'INFO')

    return {
        'event': event,
        'event_type': _get_event_type(event),
        'event_meta': meta
    }
