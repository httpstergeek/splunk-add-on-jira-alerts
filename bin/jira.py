import sys
import json
import requests
import gzip
import csv
from jira_helpers import get_jira_password

# creates outbound message from alert payload contents
# and attempts to send to the specified endpoint
def send_message(payload):
    config = payload.get('configuration')
    inline = config.get('inline')
    description = config.get('description')
    search = "saved search name:\n%s" % (payload.get('search_name')) if config.get('search_name') else ""
    link = "results link:\n%s" % (payload.get('results_link')) if config.get('link_to_results') else ""

    # Reads results gz file
    if inline:
        inline = ""
        with gzip.open(payload.get('results_file')) as f:
            csvfile = "%s" % f.read()
            csvfile = csvfile.splitlines()
            rdr = csv.reader(csvfile)
            inline = "results:\n"
            for r in rdr:
                rlen = len(r)
                inline += ",".join(r[:rlen-2]) + "\n"

    description = '\n\n'.join([description, inline, search, link])

    ISSUE_REST_PATH = "/rest/api/latest/issue"
    url = config.get('jira_url')
    jira_url = url + ISSUE_REST_PATH
    username = config.get('jira_username')
    password = get_jira_password(payload.get('server_uri'), payload.get('session_key'))

    # create outbound JSON message body
    body = json.dumps({
        "fields": {
            "project": {
                "key" : config.get('project_key')
            },
            "summary": config.get('summary'),
            "description": description,
            "issuetype": {
                "name": config.get('issue_type')
            }
        }
    })

    # create outbound request object
    try:
        headers = {"Content-Type": "application/json"}
        result = requests.post(url=jira_url, data=body, headers=headers, auth=(username, password))
        print >>sys.stderr, "INFO Jira server HTTP status= %s" % result.text
        print >>sys.stderr, "INFO Jira server response: %s" % result.text
    except Exception, e:
        print >> sys.stderr, "ERROR Error sending message: %s" % e
        return False

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--execute":
        try:
            # retrieving message payload from splunk
            raw_payload = sys.stdin.read()
            payload = json.loads(raw_payload)
            send_message(payload)
        except Exception, e:
            print >> sys.stderr, "ERROR Unexpected error: %s" % e
            sys.exit(3)
    else:
        print >> sys.stderr, "FATAL Unsupported execution mode (expected --execute flag)"
        sys.exit(1)
