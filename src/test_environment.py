#!/usr/bin/env python3
"""
Copyright 2018 Nordnet Bank AB
Permission is hereby granted, free of charge, to any person obtaining a copy of
this software and associated documentation files (the "Software"), to deal in
the Software without restriction, including without limitation the rights to
use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies
of the Software, and to permit persons to whom the Software is furnished to do
so, subject to the following conditions:
The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.
THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

import base64
import http.client
import json
import socket
import ssl
import sys
import time
from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_v1_5
from multiprocessing import Process
import requests


# global variables with static information about nExt API
SERVICE = 'NEXTAPI'
API_VERSION = '2'
API_URL = 'api.test.nordnet.se'
PUBLIC_KEY_FILENAME = 'NEXTAPI_TEST_public.pem'
SERVICE_NAME = 'NEXTAPI'


def get_hash(username, password, public_key_filename):
    """
    Helper function to encrypt with the public key provided
    """
    timestamp = int(round(time.time() * 1000))
    timestamp = str(timestamp).encode('ascii')

    username_b64 = base64.b64encode(username.encode('ascii'))
    password_b64 = base64.b64encode(password.encode('ascii'))
    timestamp_b64 = base64.b64encode(timestamp)

    auth_val = username_b64 + b':' + password_b64 + b':' + timestamp_b64
    # Need local copy of public key for NEXT API in PEM format

    try:
        public_key_file_handler = open(public_key_filename).read()
    except IOError:
        print("Could not find the following file: ",
              "\"", public_key_filename, "\"", sep="")
        sys.exit()
    rsa_key = RSA.importKey(public_key_file_handler)
    cipher_rsa = PKCS1_v1_5.new(rsa_key)
    encrypted_hash = cipher_rsa.encrypt(auth_val)
    encoded_hash = base64.b64encode(encrypted_hash)

    return encoded_hash

def connect_to_feed(public_feed_hostname, public_feed_port):
    """
    Connect to the feed and get back a TCP socket
    """
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    if public_feed_port == 443:
        s = ssl.wrap_socket(s)
    s.connect((public_feed_hostname, public_feed_port))
    return s

def send_cmd_to_socket(socket, cmd):
    """
    Send commands to the feed through the socket
    """
    socket.send(bytes(json.dumps(cmd) + '\n', 'utf-8'))
    print("<< Sending cmd to feed: " + str(cmd))

def try_parse_into_json(string):
    """
    Try parsing the string into JSON objects. Return the unparsable
    parts as buffer
    """
    json_strings = string.split('\n')

    for i in range(0, len(json_strings)):
        try:
            json_data = json.loads(json_strings[i])
            print(">> JSON udpates from public feed")
            print(json.dumps(json_data, indent=4, sort_keys=True))
        except:
            ## If this part cannot be parsed into JSON, It's probably not
            ## complete. Stop it right here. Merge the rest of list and
            ## return it, parse it next time
            return ''.join(json_strings[i:])

    ## If all JSONs are successfully parsed, we return an empty buffer
    return ''

def do_receive_from_socket(socket, last_buffer):
    """
    Receive data from the socket, and try to parse it into JSON. Return
    the unparsable parts as buffer
    """
    # Consume message (price data or heartbeat) from public feed
    #> Note that a full message with all the JSON objects ends with a
    #> newline symbol "\n". As such you need to listen and read from
    #> the buffer until a full message has been transferred
    time.sleep(0.01)
    new_data = socket.recv(1024).decode('utf-8')

    string = last_buffer + new_data
    if string != '':
        new_buffer = try_parse_into_json(string)
        return new_buffer

    return ''

def receive_message_from_socket(socket):
    """
    Receive data from the socket and parse it
    """
    print('\nStarting receiving from socket...\n')
    buffer = ''
    while True:
        buffer = do_receive_from_socket(socket, buffer)
    print('\nFinishing receiving from socket...\n')


def main():
    """
    The main function
    """
    # Input username and password for your account in the test system
    if len(sys.argv) != 3:
        raise Exception('To run test_program you need to provide as arguments [USERNAME] [PASSWORD]')
    USERNAME = sys.argv[1]
    PASSWORD = sys.argv[2]
    auth_hash = get_hash(USERNAME, PASSWORD, PUBLIC_KEY_FILENAME)

    headers = {"Accept": "application/json"}

    # Alternative login
    print("Test login")
    login = requests.post('https://api.test.nordnet.se/next/2/login/', data={'service':SERVICE_NAME, 'auth':auth_hash}, headers=headers)
    login = json.loads(login.text)
    public_feed_hostname = login["public_feed"]["hostname"]
    public_feed_port = login["public_feed"]["port"]
    our_session_key = login["session_key"]
    print(login)


    markets = requests.get('https://api.test.nordnet.se/next/2/markets/', auth=(our_session_key, our_session_key), headers=headers)
    print("Get countries")
    markets = json.loads(markets.text)

    print(markets)
    for c in markets:
        try:
            marked_id, country, name = c['market_id'], c['country'], c['name']
            print(marked_id, country, name)

        except:
            print('Did not find code')


    # Establish connection to public feed
    print("\nConnecting to feed " + str(public_feed_hostname) + ":" + str(public_feed_port) + "...\n")
    feed_socket = connect_to_feed(public_feed_hostname, public_feed_port)

    # Start a parallel process that keeps receiving updates from the TCP socket
    proc = Process(target=receive_message_from_socket, args=(feed_socket,))
    proc.start()

    # Login to public feed with our session_key from NEXT API response
    cmd = {"cmd": "login", "args": {"session_key": our_session_key, "service": "NEXTAPI"}}
    send_cmd_to_socket(feed_socket, cmd)

    # Subscribe to ERIC B price in public feed
    cmd = {"cmd": "subscribe", "args": {"t": "price", "m": 11, "i": "101"}}
    send_cmd_to_socket(feed_socket, cmd)

    console_input = ""
    while console_input != "exit":
        console_input = input()
        try:
            cmd = json.loads(console_input)
            send_cmd_to_socket(feed_socket, cmd)
        except Exception as e:
            print(e)


    feed_socket.shutdown(socket.SHUT_RDWR)
    feed_socket.close()
    sys.exit(0)


main()
