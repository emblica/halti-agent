from queue import Queue
from halti_agent.statekeeper import determine_container_actions, StatekeeperWorker, current_and_desired
from time import sleep

UUID1 = '90d59a42-ff2b-4747-8692-290fe933d421'
UUID2 = '90d59a42-ff2b-4747-8692-290fe933d422'
UUID3 = '90d59a42-ff2b-4747-8692-290fe933d423'

HALTI_SERVICE_FIELDS = ['instances', 'cpu', 'ports', 'service_id', 'enabled',
                        'environment', 'image', 'name', 'memory', 'version']

def mock_service(uuid, name, version):
    """Mock Halti Service."""
    return {
        'service_id': uuid,
        'name': name,
        'version': version,
        'instances': 1,
        'ports': [{'protocol': 'tcp', 'port': 80}],
        'memory': 100,
        'cpu': 0.1,
        'environment': [{
            'value': '80',
            'key': 'PORT'
        }],
        'enabled': True,
        'image': 'tutum/hello-world'
    }


def mock_container(name, version, id='6e1f8c1a0038672825b2a6dd6'):
    """Mock Docker client's container dict."""
    return {
        'Ports': [{
            'PublicPort': 4040,
            'PrivatePort': 4040,
            'IP': '127.0.0.1',
            'Type': 'tcp'
        }],
        'NetworkSettings': {
            'Networks': {
                'bridge': {
                    'IPAMConfig': None,
                    'IPPrefixLen': 16,
                    'IPAddress': '172.17.0.4',
                    'GlobalIPv6Address': '',
                    'Aliases': None,
                    'EndpointID': '0f25286fab3f984dc4755f637ad5055c7e204c99eeea3b74964bf2c7814ca5ab',
                    'MacAddress': '02:42:ac:11:00:04',
                    'IPv6Gateway': '',
                    'GlobalIPv6PrefixLen': 0,
                    'Gateway': '172.17.0.1',
                    'Links': None,
                    'NetworkID': 'b6355c3f37a4de97c7e128157012b00f8a67afb74e0128dc50c74c6e806b9723'
                }
            }
        },
        'Command': 'java -jar app-standalone.jar',
        'ImageID': 'sha256:c71dd2c9bd5ec8cd3de72c64d691d2efe57faf6831dda8a9a6e47223d6dfe81e',
        'Labels': {'version': version},
        'Status': 'Up 49 minutes',
        'Names': ['/' + name],
        'Created': 1474885093,
        'Mounts': [],
        'Id': id,
        'State': 'running',
        'HostConfig': {'NetworkMode': 'default'},
        'Image': 'emblica/test'
    }


def mock_heartbeat(services):
    return {
        'heartbeat': '2016-09-26T10:45:44.605Z',
        'alive': True,
        'services': services
    }


def test_determine_container_actions():
    """to_remove and to_start should be corectly calculated."""
    current = desired = []
    to_remove, to_start = determine_container_actions(
        *current_and_desired(current, desired)
    )
    assert to_remove == to_start == set([])

    current = []
    desired = [mock_service(UUID1, 'hello1', 'v1')]
    to_remove, to_start = determine_container_actions(
        *current_and_desired(current, desired)
    )
    assert to_remove == set([])
    assert to_start == {UUID1}

    current = [mock_container('hello1', 'v1')]
    desired = [mock_service(UUID2, 'hello2', 'v2')]
    to_remove, to_start = determine_container_actions(
        *current_and_desired(current, desired)
    )
    assert to_remove == {'hello1'}
    assert to_start == {UUID2}

    current = [mock_container('hello1', 'v2')]
    desired = [
        mock_service(UUID1, 'hello1', 'v1'),
        mock_service(UUID2, 'hello2', 'v2'),
        mock_service(UUID3, 'hello3', 'v3'),
    ]
    to_remove, to_start = determine_container_actions(
        *current_and_desired(current, desired)
    )
    assert {'hello1'} == to_remove
    assert {UUID1, UUID2, UUID3} == to_start


def test_statekeeper_thread():

    mock_queue = Queue()

    class MockContainerClient(object):
        """Mock container_client that counts how its methods are called."""
        current = [mock_container('hello1', 'v2', id='foobar')]
        to_start = {UUID1, UUID2, UUID3}

        def __init__(self):
            """Init call counters."""
            self.list_called = self.stop_and_remove_called = self.start_called = 0

        def list_containers(self):
            """Just count call times."""
            self.list_called += 1
            return self.current

        def stop_and_remove(self, container_id):
            """assert the correct container is removed."""
            self.stop_and_remove_called += 1
            assert container_id == 'foobar'

        def start_container(self, spec):
            """assert correct services in spec."""
            self.start_called += 1
            assert spec['service_id'] in self.to_start
            self.to_start.remove(spec['service_id'])
            assert set(spec.keys()) == set(HALTI_SERVICE_FIELDS)

    container_client = MockContainerClient()

    statekeeper = StatekeeperWorker(mock_queue, container_client=container_client)
    statekeeper.daemon = True
    statekeeper.start()

    mock_queue.put(mock_heartbeat([
        mock_service(UUID1, 'hello1', 'v1'),
        mock_service(UUID2, 'hello2', 'v2'),
        mock_service(UUID3, 'hello3', 'v3'),
    ]))

    sleep(0.01)  # wait so Statekeeperhas time to do it's thing
    assert container_client.list_called == 1
    assert container_client.stop_and_remove_called == 1
    assert container_client.start_called == 3
