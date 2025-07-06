
## Configuring Containerized Nominatim on Ubuntu

Nominatim API calls work asynchronously with Nominatim's PostgreSQL-native framework and work quickly on modern machines.

Download Ubuntu WSL and follow instructions on 'https://github.com/mediagis/nominatim-docker/tree/master/5.1'

Run the following commands to setup and run the Nominatim Docker container runtime:

```bash
mkdir -p ~/osm-data

cd ~/osm-data

wget https://download.geofabrik.de/asia/armenia-latest.osm.pbf


docker run -it \
  -v nominatim-flatnode:/nominatim/flatnode \
  -v ~/osm-data:/data \
  -e PBF_PATH=/data/armenia-latest.osm.pbf \
  -e REPLICATION_URL=https://download.geofabrik.de/asia/armenia-updates/ \
  -e POSTGRES_EFFECTIVE_CACHE_SIZE=16GB \
  -e POSTGRES_MAINTENANCE_WORK_MEM=8GB \
  -v nominatim-data:/var/lib/postgresql/16/main \
  -p 8080:8080 \
  --name nominatim \
  mediagis/nominatim:5.1

```


Ensure `POSTGRES_SHARED_BUFFERS` is roughly 25% of your system RAM and `POSTGRES_EFFECTIVE_CACHE_SIZE` is 50–75% of your system RAM.

## Exposing WSL Ports

If running on WSL for Ubuntu, PORT 8080 will need to be opened with Windows PowerShell:
```ps1
    netsh interface portproxy add v4tov4 listenport=8080 listenaddress=0.0.0.0 connectport=8080 connectaddress=[WSL_IP_ADDRESS] protocol=tcp
```

The WSL IP can found obtained using:
```bash
hostname -I | awk '{print $1}'
```

## Testing Nominatim

Once Nominatim has finished importing the data file for Armenia (1-4 Minutes) you can test a request for "Yerevan" to make sure the server is up and running:

```
http://localhost:8080/search.php?q=Yerevan&format=json&addressdetails=1&accept-language=en
```

See 'https://nominatim.org/release-docs/latest/api/Search/'


## Starting and Stopping

To stop and restart the Nominatim service:

```bash
    docker stop nominatim
    docker rm nominatim
    docker start nominatim
```


