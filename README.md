# API server for "Nagios Slash command" app in Slack

You can use this Docker image to host the server needed for the "Nagios Slash Command" app in Slack

Requirements: 
- [nagios-api](https://github.com/zorkian/nagios-api) (runs on your Nagios server)
- Connectivity from this Docker container to [nagios-api](https://github.com/zorkian/nagios-api)
- Publicly accessible from internet with valid certificate (setup any NAT required for Slack to be able to reach this server)

__Be sure to create your own config.ini file from the provided config.ini.example file__

The Docker image runs Flask via Apache WSGI

The command to run the `Dockerfile` is:

`docker run -d -p 80:80 --name <name> apache-flask`

Slack requires HTTPS, so you can stick a load balancer in front of this server for SSL termination

## Syntax

Currently, only the "Schedule Downtime" command is available.

From Slack:
`<Slash command> <hostname in Nagios> [duration] [comment]`

- hostname: Hostname as it appears in Nagios for the host you'd like to schedule downtime for
- (optional) duration: Enter the duration of the downtime. If not units are specified, seconds are used. Valid units are 'm','h','d' for minutes, hours, days, respectively.
- (optional) comment: Enter a descriptive comment for the downtime if you'd like

The "schedule downtime" command gets sent to the nagios-api server, along with the username in Slack. If the command was successful on the nagios-api server, we send a JSON response back to Slack, which gets displayed in a "pretty" form to the user:

## Example

From Slack:
`/nagios elk 1m`

Server JSON response:
```json
{
  "text": "Success!",
  "response_type": "in_channel",
  "attachments": [
    {
      "text": "Successfully set a downtime of 1 minute for elk"
    }
  ]
}
```

Response as seen in Slack (channel-wide):
![Response in Slack](http://i.imgur.com/EH5RFkI.png)
