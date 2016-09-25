# Halti-client


## Build
```
docker build -t emb/halti-agent .
```

## Environment
```
DOCKER_TLS_VERIFY=1
DOCKER_HOST=tcp://192.168.99.100:2376
DOCKER_CERT_PATH=/Users/dockeruser/.docker/machine/machines/default
HALTI_SERVER=http://localhost:4040
PORT_BIND_IP=192.168.99.100
```

## Run
```
docker run -it --privileged -v /var/run/docker.sock:/var/run/docker.sock -e DOCKER_HOST=unix:///var/run/docker.sock -e HALTI_SERVER=http://192.168.100.106:4040 -e PORT_BIND_IP=192.168.99.100 emb/halti-agent
```

## Special features

Into every container there is `HALTI_SERVICE_ID`-environment variable which is populated by service-id of the service.

This ENV-var overrides possible clashing environment-vars
