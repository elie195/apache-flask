# API server for "Nagios Slash command" app in Slack

You can use this Docker image to host the server needed for the "Nagios Slash Command" app in Slack

Requirements: 
- nagiosapi (runs on your Nagios server)
- Connectivity from this Docker container to nagiosapi
- Publicly accessible from internet with valid certificate (setup any NAT required for Slack to be able to reach this server)


*Be sure to create your own config.ini file from the provided config.ini.example file*

The Docker image runs Flask via Apache WSGI

The command to run the `Dockerfile` is:

`docker run -d -p 80:80 --name <name> apache-flask`

Slack requires HTTPS, so you can stick a load balancer in front of this server for SSL termination
