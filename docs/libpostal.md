# Using Libpostal-FastAPI in a Containerized Ubuntu Environment (WSL2)

This guide sets up a high-performance, containerized Libpostal REST API using [libpostal-fastapi](https://github.com/alpha-affinity/libpostal-fastapi). It’s ideal for asynchronous, scalable address parsing from Python using libraries like `aiohttp`.

---

## Prerequisites

- A working version of **Ubuntu** on WSL2 which has Docker installed.
- https://www.supportyourtech.com/tech/how-to-install-ubuntu-on-windows-11-a-step-by-step-guide/

---

## Setup Instructions

### 1. Clone the Repository

```bash
git clone https://github.com/alpha-affinity/libpostal-fastapi.git
cd libpostal-fastapi
```

### 2. Build the Docker Image

```bash
docker build . -t libpostal-fastapi
```

> This will compile Libpostal, download the model data

```bash
docker run -it --rm -p 8001:8001 libpostal-fastapi
```

> This will begin the FastAPI server for API calls

---

## API Endpoints

LibPostal FastAPI can be tested with `curl` in WSL:

```bash
curl 'http://localhost:8001/parse?address=30+w+26th+st,+new+york,+ny&language=en&country=us'
```

Response:
```json
[["30","house_number"],["w 26th st","road"],["new york","city"],["ny","state"]]
```

> Full API docs: [http://localhost:8001/docs](http://localhost:8001/docs)

---

## Stopping Running Containers

```bash
docker stop $(docker ps -q)
```

Or use `docker ps` to view and stop the container ID.

## Notes

- The Libpostal models are loaded once at startup — then responses are quick.
- The API supports `/parse`, `/expand`, and `/expandparse`.


## Optional: Exposing WSL Ports to Windows or Other Devices

If you're running Libpostal inside WSL2 and need to access it from outside WSL (e.g., from another device or app), you may need to forward port 8001 manually:

```ps1
netsh interface portproxy add v4tov4 listenport=8001 listenaddress=0.0.0.0 connectport=8001 connectaddress=[WSL_IP_ADDRESS] protocol=tcp
```

The WSL IP can found in WSL using:
```bash
hostname -I | awk '{print $1}'
```
---

