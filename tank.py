#!/usr/bin/env python
# coding: utf8

import requests
import json
from datetime import datetime

headers = {
    "Host": "travels.com",
    "User-Agent": "tank",
    "Accept": "*/*",
    "Connection": "Close",
}

# path_to_ammo = '/path/to/data/FULL/{}/{}'
path_to_ammo = '/path/to/data/TRAIN/{}/{}'
host_template = 'http://localhost:8080{}'

ignore_results = False


def check_get(answer_name):
    i = 0
    tm = 0
    t_min = 100000
    t_max = 0
    with open(path_to_ammo.format('answers', answer_name), "r") as f:
        for line in f.readlines():
            vals = line.strip().split("\t")

            before = datetime.now()
            r = requests.get(host_template.format(vals[1]),
                             headers=headers)
            after = datetime.now()
            df = (after - before).microseconds
            tm += df
            if df > t_max:
                t_max = df
            if df < t_min:
                t_min = df
            i += 1
            if not ignore_results:
                if r.status_code != int(vals[2]):
                    print("ERROR: code mismatch")
                    print("Expected: {}, but received: {}".format(
                        vals[2], r.status_code))
                    print(line)
                if r.status_code != 200:
                    continue
                expected = json.loads(vals[3])
                received = r.json()
                if expected != received:
                    print("ERROR: answer mismatch")
                    print("Expected: ", expected)
                    print("Received: ", received)
                    print(line)
                    print

    print("avg: {}".format(tm / i))
    print("min: {}, max: {}".format(t_min, t_max))


def check_post(ammo_name, answer_name):
    i = 0
    tm = 0
    t_min = 100000
    t_max = 0
    with open(path_to_ammo.format('ammo', ammo_name), "r") as ammo:
        with open(path_to_ammo.format('answers', answer_name), "r") as answer:
            for line in answer.readlines():
                answer_vals = line.strip().split("\t")
                # 312 POST:/locations/<entity_id>
                # POST /locations/110?query_id=0 HTTP/1.1
                # Host: travels.com
                # User-Agent: tank
                # Accept: */*
                # Connection: Close
                # Content-Length: 145
                # Content-Type: application/json
                #
                # {"distance": 61, "country": "\u0428\u0432\u0435\u0439\u0446\u0430\u0440\u0438\u044f", "city": "\u041c\u0443\u0440\u043b\u0430\u043c\u0441\u043a"}
                ammo.readline()
                req_line = ammo.readline().strip()
                req = req_line.split(" ")
                if (req[0] != answer_vals[0] or req[1] != answer_vals[1]):
                    print("ERROR: request/answer mismatch")
                    print("Request: ", req_line)
                    print("Response: ", line)
                empty = False
                for _ in range(0, 6):
                    l = ammo.readline().strip()
                    if l.startswith('Content-Length'):
                        _, content_length = l.split(' ')
                    if l == '':
                        empty = True
                        break
                if not empty and content_length != "0":
                    ammo.readline()
                    payload = ammo.readline().strip()
                elif content_length == "0":
                    ammo.readline()
                    payload = ''
                else:
                    payload = ''
                before = datetime.now()
                r = requests.post(host_template.format(answer_vals[1]),
                                  headers=headers, data=payload)
                after = datetime.now()
                df = (after - before).microseconds
                tm += df
                if df > t_max:
                    t_max = df
                if df < t_min:
                    t_min = df
                i += 1
                if not ignore_results:
                    if r.status_code != int(answer_vals[2]):
                        print("ERROR: code mismatch")
                        print("Expected: {}, but received: {}".format(
                            answer_vals[2], r.status_code))
                        print(line)
    print("avg: {}".format(tm / i))
    print("min: {}, max: {}".format(t_min, t_max))


check_get('phase_1_get.answ')
check_post('phase_2_post.ammo', 'phase_2_post.answ')
check_get('phase_3_get.answ')
