import json
import os
import docker
import requests
import multiprocessing
import platform
from threading import Thread
import time
from queue import Queue, Empty
from docker import Client
from docker.utils import kwargs_from_env
import signal
import sys

PORT_BIND_IP = os.environ.get('PORT_BIND_IP', '192.168.99.100')

halti_server_url = os.environ.get('HALTI_SERVER', 'http://localhost:4040')
allow_insecure_registry = os.environ.get('ALLOW_INSEC_REGISTRY', 'FALSE') == 'TRUE'
state_file_path = 'state.json'
state = {}

options = kwargs_from_env()
options['version'] = '1.20'

client = Client(**options)
agent_state_queue = Queue()

heartbeating = True
statekeeping = True

def load_state():
  try:
      with open(state_file_path, 'r') as state_file:
        state = json.load(state_file)
        state_file.close()
        return state
  except Exception as e:
      return {}

def save_state(state):
  with open(state_file_path, 'w') as state_file:
    json.dump(state, state_file)
    state_file.close()
    return True
  return False

def post_json(url, payload):
    headers = {'Content-Type': 'application/json'}
    data = json.dumps(payload)
    return requests.post(url, data=data, headers=headers)

def register(state, client):
  if state.get('instance_id', False):
    return state['instance_id'], state['heartbeat_interval']
  register_url = halti_server_url + '/api/v1/instances/register'
  system = {"cpus": multiprocessing.cpu_count(),
            "system": platform.system(),
            "system_version": platform.version(),
            "hostname": platform.node()}
  payload = {"info": client.info(), "system": system, "client": client.version()}
  r = post_json(register_url, payload)
  resp = r.json()
  return resp['instance_id'], resp['heartbeat_interval']


def halti_containers():
    return client.containers(filters={"label":"halti"})


def generate_environment_vars(env_list):
    en = {}
    for env_pair in env_list:
        en[env_pair['key']] = env_pair['value']
    return en

def start_container(specs):
    image = client.pull(specs['image'], stream=True, insecure_registry=allow_insecure_registry)
    for status_json in image:
        status = json.loads(status_json.decode('utf-8'))
    env = generate_environment_vars(specs['environment'])
    ports = {}
    for port in specs['ports']:
        ports[int(port)] = (PORT_BIND_IP,)
    #specs.get('command', None)
    labels = {
              "halti": "true",
              "service": specs['name'],
              "version": specs['version']
             }
    host_conf = client.create_host_config(restart_policy={"Name": "always"},
                                          port_bindings=ports)
    container = client.create_container(image=specs['image'],
                                     name=specs['service_id'],
                                     ports=specs['ports'],
                                     environment=env,
                                     labels=labels,
                                     host_config=host_conf)
    client.start(container=container.get('Id'))


def heartbeating_loop(state):
    global heartbeating
    while heartbeating:
        hb = heartbeat(state)
        if hb:
            agent_state_queue.put(hb, True, 5)
        time.sleep(state['heartbeat_interval'])


def heartbeat(state):
  print("Heartbeat!")
  try:
      heartbeat_url = halti_server_url + '/api/v1/instances/' + state['instance_id'] + '/heartbeat'
      payload = {"containers": halti_containers()}
      r = post_json(heartbeat_url, payload)
      resp = r.json()
      return resp
  except Exception as e:
    print(e)
    return None

def set_state(state):
    service_list = state['services']
    old_service_list = halti_containers()
    services = {}
    old_services = {}
    for service in service_list:
        service_id = service['service_id']
        services[service_id] = service

    for old_service in old_service_list:
        old_service_id = old_service['Names'][0][1:]
        old_services[old_service_id] = old_service

    services_to_remove = set(old_services.keys()) - set(services.keys())
    services_to_check = set(old_services.keys()) & set(services.keys())
    services_to_start = set(services.keys()) - set(old_services.keys())

    for service_id in services_to_check:
        new_service = services[service_id]
        old_service = old_services[service_id]
        if new_service['version'] != old_service['Labels']['version']:
            services_to_remove.add(service_id)
            services_to_start.add(service_id)


    for service_id in services_to_remove:
        print("removing", service_id)
        container_id = old_services[service_id]['Id']
        client.stop(container_id)
        client.remove_container(container_id)
    for service_id in services_to_start:
        print("starting", service_id)
        service = services[service_id]
        start_container(service)

def statekeeper_loop(a):
    global statekeeping
    while statekeeping:
        try:
            agent_state = agent_state_queue.get(True, 1)
            try:
                set_state(agent_state)
            except Exception as e:
                print(e)
            agent_state_queue.task_done()
        except Empty as e:
            pass

state = load_state()
state['instance_id'], state['heartbeat_interval'] = register(state, client)
save_state(state)


# Starting heartbeat
hb_thread = Thread(target=heartbeating_loop, args=(state,))
hb_thread.start()
statekeeper_thread = Thread(target=statekeeper_loop, args=(None,))
statekeeper_thread.start()


def signal_handler(signal, frame):
        print('Stopping agent...')
        global heartbeating
        global statekeeping
        heartbeating = False
        statekeeping = False
        statekeeper_thread.join(1)
        hb_thread.join(1)
        sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.pause()
