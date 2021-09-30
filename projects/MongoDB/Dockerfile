FROM mongo:bionic
RUN apt-get update -y && apt-get install -y bash vim
COPY . ./docker-entrypoint-initdb.d/
