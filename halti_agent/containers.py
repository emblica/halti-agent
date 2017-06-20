"""
Containers module uses and abstracts away the docker_client.

There are currently no plans to support other containers than Docker,
but we try keep this as a possibility.
"""
import logging

from halti_agent import comms, settings
from halti_agent.func_utils import env_pairs_to_dict

from docker import Client
from docker.errors import DockerException

logger = logging.getLogger('halti-agent')

logger.info('starting docker client with {}'.format(settings.DOCKER_OPTIONS))
docker_client = Client(**settings.DOCKER_OPTIONS)


def list_containers():
    """Return containers managed by Halti."""
    return docker_client.containers(filters={'label': 'halti'})


def stop_and_remove(container_id):
    """Stop and remove the provided container."""
    docker_client.stop(container_id)
    docker_client.remove_container(container_id)


def pull_container(image):
    """Pull a container. Relays image to docker_client.pull."""
    docker_client.pull(image, insecure_registry=settings.ALLOW_INSECURE_REGISTRY)


def start_container(spec):
    """Start a Docker container as per the given spec (= Halti Service)"""
    comms.notify_master(comms.Events.PULL_START, spec['image'])
    try:
        pull_container(spec['image'])
    except DockerException as ex:
        logger.error('DockerException: pulling image. {}'.format(ex), exc_info=True)
        comms.notify_master(comms.Events.PULL_FAILED, str(ex))
        return

    env = env_pairs_to_dict(spec['environment'])
    env['HALTI_SERVICE_ID'] = spec['service_id']

    ports = {}
    ports_declaration = []

    for port in spec['ports']:

        is_digit = lambda port: hasattr(port, 'isdigit') and port.isdigit()

        if type(port) is int or is_digit(port):
            # for backwards compatibility
            ports_declaration.append(port)
            ports[int(port)] = (settings.PORT_BIND_IP,)
        else:
            # port, protocol = port['port'], port['protocol']
            k = '{}/{}'.format(port['port'], port['protocol'])
            if port['protocol'] == 'udp':
                ports_declaration.append((port['port'], 'udp'))
            else:
                ports_declaration.append(port['port'])

            if 'source' in port:
                ports[k] = (settings.PORT_BIND_IP, port['source'])
            else:
                ports[k] = (settings.PORT_BIND_IP,)

    labels = {'halti': 'true',
              'service': spec['name'],
              'version': spec['version']}

    # Extract extra hosts
    extra_hosts = None
    if 'extra_hosts' in spec:
        logger.info('Extra hosts defined in spec {}'.format(spec['name']))
        extra_hosts = {}
        for host in spec['extra_hosts']:
            extra_hosts[host['host']] = host['ip']

    host_conf = docker_client.create_host_config(
        restart_policy={'Name': 'always'},
        extra_hosts=extra_hosts,

        port_bindings=ports
    )

    container_params = {
            "image": spec['image'],
            "name": spec['service_id'],
            "ports": ports_declaration,
            "environment": env,
            "labels": labels,
            "host_config": host_conf
    }
    if 'command' in spec and len(spec.get('command')) > 0:
        logger.info('Command defined in spec {}'.format(spec['name']))
        container_params['command'] = spec.get('command')

    container = docker_client.create_container(**container_params)

    comms.notify_master(comms.Events.START_CONTAINER, spec['service_id'])
    docker_client.start(container=container.get('Id'))
