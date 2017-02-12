#!/bin/bash

#This script rebuilds the image (used to test changes quickly)

docker rm -f nagiosapi
docker build -t apache-flask .
docker run -d -p 80:80 --name nagiosapi apache-flask
