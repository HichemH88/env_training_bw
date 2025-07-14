the project is a multi services virtualized environment with dokcer and docker compose:
Database service: POstgres
Micro service : API for Postgres
Python service: runtime envronment to prepare data pipelines and execute the program.

prerequisite:
VS code
docker desktop
dowload the Git link: https://github.com/HichemH88/env_training_bw
remeove the app/entrypoint.sh and receate it to avoid issue of encoding (not forgot to copy paste the script on the file)
run the docker services:
docker compose up --build --no-start
Start the container services by order:
Postgres-db
Postgrest
Python service
check the services: docker stats or docker ps -a
execute init sql: create user admin, then new schema dev and grant privielges to admin in order to configure PGREST api
