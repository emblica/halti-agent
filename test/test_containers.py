from halti_agent import containers, comms, settings
from docker.errors import DockerException

import requests_mock


def failing_pull_container(*args, **kwargs):
    """pull container that raises DockerException."""
    raise DockerException('pull failed')


def test_start_container_notifies_master_on_failure():
    """start_container should notify master if pull fails."""

    # monkeypatches
    comms.INSTANCE_ID = 'foobar-1'
    containers.pull_container = failing_pull_container

    mock_url = settings.HALTI_SERVER_URL + comms.NOTIFY_URL.format(comms.INSTANCE_ID)

    with requests_mock.mock() as m:

        m.post(mock_url, text='{}')
        containers.start_container({'image': 'tutum/hello-world'})

        assert m.called and m.call_count == 2

        assert m.request_history[0].method == 'POST'
        assert m.request_history[0].json() == {'event': 'PULL_START',
                                               'event_type': 'INFO',
                                               'event_meta': 'tutum/hello-world'}

        assert m.request_history[1].method == 'POST'
        assert m.request_history[1].json() == {'event': 'PULL_FAILED',
                                               'event_type': 'ERROR',
                                               'event_meta': str(DockerException('pull failed'))}
