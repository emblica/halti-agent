"""
statekeeper is a responsible for managing Docker Engine's state.

It receives desired state from the agent's desired_state_queue and performs
required stop/remove and run commands to reach the desired state.

Statekeeper receives all methods and classes that have side-effects as params
for testability. (see: StatekeeperWorker.__init__)
"""
import logging
from threading import Thread

from halti_agent import comms
from halti_agent.func_utils import diff

logger = logging.getLogger('halti-agent-statekeeper')


def current_and_desired(containers, desired_services):
    """Index current and desired state."""
    current = {
        # docker container name is of the form ['/container-name']
        service['Names'][0][1:]: service
        for service in containers
    }
    desired = {
        service['service_id']: service
        for service in desired_services
    }
    return current, desired


def determine_container_actions(current, desired):
    """Return services (to_remove, to_start) 2-tuple based on state.

    - to_remove contains container names
    - to_start contains Halti Service UUIDs
    """
    to_remove, to_start, to_check = diff(current, desired)

    # a service that is in both current_map and desired_map might be one that needs
    # to be updated (to be removed and to be started)
    for service_id in to_check:
        new_service, old_service = desired[service_id], current[service_id]
        if new_service['version'] != old_service['Labels']['version']:
            to_remove.add(service_id)
            to_start.add(service_id)
    return to_remove, to_start


def set_state(desired_state, container_client):
    """Remove, start or ignore containers based on current and desired state."""
    logger.debug('Setting state.')

    containers = container_client.list_containers()
    current, desired = current_and_desired(containers, desired_state['services'])
    to_remove, to_start = determine_container_actions(current, desired)

    # stop and remove
    for name in to_remove:
        logger.info('removing {}'.format(name))
        container_id = current[name]['Id']
        # Notify master
        comms.notify_master(comms.Events.STOP_CONTAINER, name)

        container_client.stop_and_remove(container_id)

    # start
    for service_id in to_start:
        logger.info('starting {}'.format(service_id))
        container_client.start_container(spec=desired.get(service_id))


class StatekeeperWorker(Thread):
    """Operate Docker on desired state updates."""

    def __init__(self, queue, container_client):
        """Init thread and give access to desired state queue."""
        logger.info('Starting statekeeper...')
        Thread.__init__(self)
        self.queue = queue
        self.container_client = container_client

    def run(self):
        """Start statekeeper in a forever loop."""
        logger.info('Statekeeper started.')
        while True:
            agent_state = self.queue.get()  # blocks until something to return
            set_state(agent_state, self.container_client)
            self.queue.task_done()
