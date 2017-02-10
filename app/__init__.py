from flask import Flask, json, request, Response, abort
import re, ConfigParser
import requests, json
from dateutil.relativedelta import relativedelta

config = ConfigParser.ConfigParser()
config.read('/var/www/apache-flask/app/config.ini')
app = Flask(__name__)

slack_token = config.get('Slack', 'slack_token')
url = config.get('Nagios', 'url')

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

@app.route("/api", methods = ['GET'])
def apicall():
    if request.args.get('token') == slack_token:
        user_name = request.args.get('user_name')
        text = request.args.get('text')
        if ' ' in text:
            parts = text.split(' ', 2)
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

    #For monitoring purposes
    elif request.args.get('ping') == "statuscake":
        return "OK"
    else:
        #This happens when the token doesn't match what's configured in Slack (probably malicious)
        abort(401)

