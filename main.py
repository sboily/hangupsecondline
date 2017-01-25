#!/usr/bin/env python

import websocket
import thread
import time
import json

from xivo_auth_client import Client as Auth
from xivo_ctid_ng_client import Client as CtidNg

wazo_host = '10.41.0.2'
username = 'sylvain'
password = 'sylvain'

started = False
lines = []
calls = {}
callcontrol = None

def on_message(ws, message):
    global started, lines

    msg = json.loads(message)

    if started:
        subscribe_events(msg, lines)
        return True
    else:
        init(ws, msg)

def on_error(ws, error):
    print error

def on_close(ws):
    print "### closed ###"

def on_open(ws):
    def run(*args):
        print "thread terminating..."
    thread.start_new_thread(run, ())

def init(ws, msg):
    global started

    if msg['op'] == 'init':
        print "INIT"
        subscribe(ws, "*")
        start(ws)

    if msg['op'] == 'start':
        started = True
        print "waiting for messages"

def subscribe_events(msg, lines):
    global calls, confd

    data = msg['data']
    name = msg['name']

    if data['status']:
        if 'call_id' in data:
            if name == 'call_created':
                calls.update({data['call_id']: name})
            if name == 'call_ended':
                if len(calls) > 0 and data['call_id'] in calls:
                    if data['status'] == 'Ringing':
                        active = None
                        for active_call in callcontrol.calls.list_calls_from_user()['items']:
                            if active_call['status'] == 'Up':
                                active = active_call['call_id']
                        for call in calls:
                            if call != active:
                                callcontrol.calls.hangup_from_user(call)
                    del calls[data['call_id']]


def subscribe(ws, event_name):
    msg = {
        'op': 'subscribe',
        'data': {
            'event_name': event_name
        }
    }

    ws.send(json.dumps(msg))

def start(ws):
    msg = {
        'op': 'start'
    }

    ws.send(json.dumps(msg))


if __name__ == "__main__":

    auth = Auth(wazo_host, username=username, password=password, verify_certificate=False)
    token_data = auth.token.new('xivo_user', expiration=3600)
    token = token_data['token']

    callcontrol = CtidNg(wazo_host, token=token, verify_certificate=False)

    websocket.enableTrace(True)
    ws = websocket.WebSocketApp("wss://{}:9502/".format(wazo_host),
                                header=["X-Auth-Token: {}".format(token)],
                                on_message = on_message,
                                on_error = on_error,
                                on_close = on_close)
    ws.on_open = on_open
    ws.run_forever(sslopt={"cert_reqs": False})
