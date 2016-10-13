import json

from docker import Client

from halti_agent import settings
from halti_agent.state import platform_state


def test_platform_state():
    """Test platform_state returns JSON serialisable data with correct keys."""
    docker_client = Client(**settings.DOCKER_OPTIONS)
    data = platform_state(docker_client)

    assert {'info', 'system', 'docker_client'} == set(data.keys())
    assert {'cpus', 'system', 'system_version', 'hostname'} == set(data.get('system').keys())

    try:
        json.dumps(data)
        assert True
    except Exception:
        assert False
