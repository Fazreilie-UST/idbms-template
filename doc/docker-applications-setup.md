# Application Container Setup on Docker 

WSL Docker Network issue
sudo mkdir -p /etc/systemd/system/docker.service.d
sudo nano /etc/systemd/system/docker.service.d/http-proxy.conf

[Service]
Environment="HTTP_PROXY=http://proxy-dmz.intel.com:912"
Environment="HTTPS_PROXY=http://proxy-dmz.intel.com:912"

save then

sudo systemctl daemon-reexec
sudo systemctl daemon-reload
sudo systemctl restart docker

## (DEVELOPMENT)

docker network create npi-network

docker run -d \
  --name pgadmin \
  --network npi-network \
  --restart=always \
  -e PGADMIN_DEFAULT_EMAIL=npi_admin@intel.com \
  -e PGADMIN_DEFAULT_PASSWORD=NPI-test \
  -v pgadmin_data:/var/lib/pgadmin \
  -p 8080:80 \
  dpage/pgadmin4:latest

docker run -d \
  --name postgresql_db \
  --network npi-network \
  --restart=always \
  -e POSTGRES_USER=npi_admin \
  -e POSTGRES_PASSWORD=NPI-test \
  -e POSTGRES_DB=npi-db \
  -v postgres_data:/var/lib/postgresql/data \
  -p 5432:5432 \
  postgres:16

docker run -d \
  --name idbms_redis \
  --network npi-network \
  --restart always \
  -p 6379:6379 \
  -v redis_data:/data \
  redis:7-alpine \
  redis-server --appendonly yes

docker volume location :  /var/lib/docker/volumes/postgresql_data/_data @ docker volume inspect <volume_name>
navigate to it : sudo ls <volume path> @ cd <volume path>


(view resource usage stats)
docker container stats

(removing container)
docker rm -f <container name>

(removing volume)
docker volume rm <volume name>

(view resource usage stats)
docker container stats


(create user-defined network)
docker network create npi-network
docker network connect pg-network postgres_db
docker network connect pg-network pgadmin
docker network inspect pg-network




## (PRODUCTION)

Docker compose 
docker run -d \
  --name pgadmin \
  --restart=always \
  -e PGADMIN_DEFAULT_EMAIL=admin@example.com \
  -e PGADMIN_DEFAULT_PASSWORD=admin123 \
  -p 8080:80 \
  dpage/pgadmin4:latest



version: "3.9"

services:
  db:
    image: postgres:16
    container_name: postgres_db
    restart: always
    environment:
      POSTGRES_USER: myuser
      POSTGRES_PASSWORD: mypassword
      POSTGRES_DB: mydatabase
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    networks:
      - pg-network

  pgadmin:
    image: dpage/pgadmin4:latest
    container_name: pgadmin
    restart: always
    environment:
      PGADMIN_DEFAULT_EMAIL: admin@example.com
      PGADMIN_DEFAULT_PASSWORD: admin123
    ports:
      - "8080:80"
    depends_on:
      - db
    networks:
      - pg-network

volumes:
  postgres_data:

networks:
  pg-network:
    driver: bridge




# Reset Dev
(Reset Docker-Dev)
docker rm -f postgres_db
docker rm -f pgadmin
docker volume rm pgadmin_data
docker volume rm postgresql_data
docker network rm npi-network


(Revert Alembic Migrations)
- verify first
python -m alembic current
python -m alembic history