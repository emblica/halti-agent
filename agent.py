import logging
from queue import Queue
import sys
import time

VERSION = '0.1.0'

import requests

from halti_agent import comms, halti_agent_info
from halti_agent import containers as container_client
from halti_agent.state import load_state
from halti_agent.statekeeper import StatekeeperWorker


logger = logging.getLogger('halti-agent')
desired_state_queue = Queue()


def heartbeat():
    """Perform a single Halti Heartbeat."""
    logger.debug('Heartbeat!')
    try:
        payload = {'containers': container_client.list_containers()}
        return comms.heartbeat(payload)
    except requests.RequestException as e:
        logger.error('Heartbeat failed: {}'.format(e))
        return None


def main_loop(state, statekeeper):
    """Check that statekeeper is running and perform Halti Heartbeats."""
    while statekeeper.is_alive():
        hb = heartbeat()
        if hb:
            desired_state_queue.put(hb)
        time.sleep(state['heartbeat_interval'])

    logger.error('Statekeeper has crashed. Exiting Halti-Agent.')
    sys.exit(-1)


if __name__ == '__main__':
    logger.info('Starting Halti-Agent...')
    logger.info('VERSION:'+VERSION)
    logger.info('Information: {}'.format(halti_agent_info()))

    # load state from STATE_FILE or Halti Master
    state = load_state(container_client)

    # save instance_id to a global so comms has access to it
    # this ID never mutates after this when the agent is running
    comms.INSTANCE_ID = state['instance_id']

    statekeeper = StatekeeperWorker(desired_state_queue, container_client=container_client)
    statekeeper.daemon = True
    statekeeper.start()

    logger.info('Starting Halti-Agent main loop (health checks and heartbeat).')
    main_loop(state, statekeeper)
