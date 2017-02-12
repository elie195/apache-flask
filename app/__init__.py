from flask import Flask, json, request, Response, abort
import re, ConfigParser
import requests, json, collections
from dateutil.relativedelta import relativedelta

config = ConfigParser.ConfigParser()
config.read('/var/www/apache-flask/app/config.ini')
app = Flask(__name__)

slack_token = config.get('Slack', 'slack_token')
test_token = config.get('Testing', 'slack_token') #For testing
url = config.get('Nagios', 'url')
auth_channels = json.loads(config.get('Slack','channels'))

headers = {'Content-Type': 'application/json'}

def postToNagios(user, host, duration, comment):
    if user:
        event_data = {'host': host, 'duration': duration, 'author': user, 'comment': comment}
        r = requests.post(url, json=event_data)
        #Log raw response due to paranoia
        print "Nagios response: %s" % r.text
        data = json.loads(r.text)
        if data['success']:
            return 'success'
        else:
            return data['content']
    else:
        return "Error: User must be specified"

def humanReadableDate(inputDate):
    attrs = ['years', 'months', 'days', 'hours', 'minutes', 'seconds']
    human_readable = lambda delta: ['%d %s' % (getattr(delta, attr), getattr(delta, attr) > 1 and attr or attr[:-1])
        for attr in attrs if getattr(delta, attr)]
    return human_readable(inputDate)

def parseDuration(duration):
    match = re.search('[a-zA-Z]', duration)
    if match:
        if re.match('^\d[mM]$', duration):
            #Minutes specified
            insensitive_minute = re.compile(re.escape('m'), re.IGNORECASE)
            minutes = insensitive_minute.sub('', duration)
            return int(minutes) * 60
        elif re.match('^\d[hH]$', duration):
            #Hours specified
            insensitive_hour = re.compile(re.escape('h'), re.IGNORECASE)
            hours = insensitive_hour.sub('', duration)
            return int(hours) * 60 * 60
        elif re.match('^\d[dD]$', duration):
            #Days specified
            insensitive_day = re.compile(re.escape('d'), re.IGNORECASE)
            days = insensitive_day.sub('', duration)
            return int(days) * 24 * 60 * 60
        else:
            #Unsupported modifier
            return None
    else:
        #Numeric duration, no conversion necessary
        return int(duration)

def createJSONResponse(text, description):
    json_resp = {"response_type": "in_channel","text": text,"attachments": [{"text": description}]}
    return json.dumps(json_resp)



# The following section is experimental. Proceed with caution

class Nagios():
    commands = ['acknowledge_problem', 'add_comment', 'cancel_downtime', 'disable_notifications', 'delete_comment', 'enable_notifications', 'log', 'status', 'restart_nagios', 'objects', 'remove_acknowledgement', 'schedule_check', 'schedule_downtime', 'schedule_hostgroup_downtime', 'state', 'submit_result']
    auth_commands = json.loads(config.get('Nagios','auth_commands'))

    help_dict = {}
    help_dict['schedule_downtime'] = { "host": "required,string","duration": "required,seconds","service": "optional,string","services_too": "optional,bool","comment": "optional,string" }

def show_help(desired_command):
    commands = Nagios().help_dict[desired_command]
    print commands
    returnString = ''
    #sorted_commands = collections.OrderedDict(sorted(commands.items()))
    for k in sorted(commands, key=commands.get, reverse=True):
        if commands[k].split(',')[0] == 'required':
            returnString = returnString + "Parameter: %-*s Type: %-*s %s\n" % (20,k,10, commands[k].split(',')[1], commands[k].split(',')[0])
        elif commands[k].split(',')[0] == 'optional':
            returnString = returnString + "Parameter: %-*s Type: %-*s (%s)\n" % (20,k,10, commands[k].split(',')[1], commands[k].split(',')[0])
    return returnString

# The following endpoint can accept many different commands
# The commands must be defined in your config.ini file in order to be allowed
#
# The following commands are currently available:
#   - schedule_downtime
#
# Syntax to invoke API from Slack:
#   /api <command> <param1=value> <param2=value>
#
# Most commands require at least one argument (param key/value pair)
# To list the available arguments for a given command,
# Run the command with no arguments

@app.route("/nagios", methods = ['POST'])
def nagiosapicall():
    token = request.form["token"]
    if token == test_token:
        text = request.form["text"]
        if ' ' in text:
            desired_command = text.split(' ')[0]
            if desired_command in Nagios().auth_commands:
                if desired_command in Nagios.commands:
                    host = text.split(' ', 2)[1]
                    args = text.split(' ', 2)[2]
                    try:
                        arg_dict = dict(item.split("=") for item in args.split(" "))
                        return "Host: " + host + " " + str(arg_dict)
                    except:
                        return "Error: bad syntax. Use /api <command> <param1=value> <param2=value>"
            else:
                return "Unauthorized command. Details: command not authorized in config file"
        else:
            #Help triggered
            desired_command = text
            if desired_command in Nagios().auth_commands:
                if desired_command in Nagios().commands:
                    return show_help(desired_command)
            else:
                return "Unauthorized command. Details: command not authorized in config file"
    else:
        abort(401)

# End experimental section

@app.route("/api", methods = ['GET'])
def apicall():
    if request.args.get('token') == slack_token:
        channel = request.args.get('channel_name')
        if channel in auth_channels:
            user_name = request.args.get('user_name')
            text = request.args.get('text')
            if ' ' in text:
                parts = text.split(' ', 2) #As long as the comment is the last arg, spaces are parsed just fine
                parts += [None] * (3 - len(parts)) # Assume we can have max. 3 items. Fill in missing entries with None.
                host,duration,comment = parts
                if duration == None:
                    duration = 120
                if comment == None:
                    comment = 'Sent from Slack'
            else:
                host,duration,comment = text,120,'Sent from Slack'
            extendedDuration = parseDuration(str(duration))
            if extendedDuration != None:
                result = postToNagios(user_name, host, extendedDuration, comment)
                if result == 'success':
                    newDuration = humanReadableDate(relativedelta(seconds=extendedDuration))
                    json_resp = createJSONResponse("Success!","Successfully set a downtime of %s for %s" % (" ".join(newDuration), host))
                    resp = Response(json_resp)
                    resp.headers['Content-Type'] = 'application/json'
                    return resp
                else:
                    return "Error setting downtime. Details: %s" % result
            else:
                return "Error: Unsupported time modifier. Use 'm' for minutes, 'h' for hours, 'd' for days."
        else:
            return "Error: Unauthorized channel"

    #For monitoring purposes
    elif request.args.get('ping') == "statuscake":
        return "OK"
    else:
        #This happens when the token doesn't match what's configured in Slack (probably malicious)
        abort(401)