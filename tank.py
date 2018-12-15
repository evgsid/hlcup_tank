#!/usr/bin/env python
# coding: utf8

import argparse
import json
import os
import requests
from datetime import datetime

headers_post = {
    "Host": "accounts.com",
    "User-Agent": "Technolab/1.0 (Docker; CentOS) Highload/1.0",
    "Accept": "*/*",
    "Connection": "close",
    "Content-Type": "application/json",
}

headers_get = {
    "Host": "accounts.com",
    "User-Agent": "Technolab/1.0 (Docker; CentOS) Highload/1.0",
    "Accept": "*/*",
    "Connection": "keep-alive",
}

path_to_ammo = ''
host = ''

ignore_results = False


class RequestTime(object):
    def __init__(self):
        self.count = 0
        self.total_time = 0
        self.t_min = 100000
        self.t_max = 0

    def add(self, before, after):
        df = (after - before).microseconds
        self.total_time += df
        if df > self.t_max:
            self.t_max = df
        if df < self.t_min:
            self.t_min = df
        self.count += 1

    def print_time(self):
        print("avg: {}".format(self.total_time / self.count))
        print("min: {}, max: {}".format(self.t_min, self.t_max))


def get_expected_results(line):
    # The typical answer line is:
    # <type>  <request>  <response code> [<response body>]
    vals = line.strip().split("\t")
    # Add missed <response_body> if absent.
    if len(vals) == 3:
        vals.append(None)
    return vals[1:]


def check_response(response, expected_response_code, expected_response_body):
    if ignore_results:
        return
    if response.status_code != int(expected_response_code):
        print("ERROR: code mismatch")
        print("Expected: {}, but received: {}".format(
            expected_response_code, response.status_code))
        print(answer_line)
        print
        return

    expected = (json.loads(expected_response_body) if
                expected_response_body else "")
    try:
        received = response.json()
    except ValueError:
        received = ""
    if expected != received:
        print("ERROR: answer mismatch")
        print("Expected: {}".format(expected))
        print("Received: {}".format(received))
        print(answer_line)
        print


def check_get(answer_name):
    request_time = RequestTime()
    session = requests.Session()
    with open(os.path.join(path_to_ammo, "answers", answer_name), "r") as f:
        for answer_line in f.readlines():
            request, expected_response_code, expected_response_body = (
                get_expected_results(answer_line))

            before = datetime.now()
            response = session.get(host + request,
                                   headers=headers_get)
            after = datetime.now()
            request_time.add(before, after)
            check_response(response, expected_response_code,
                           expected_response_body)

    request_time.print_time()


def check_post(ammo_name, answer_name):
    request_time = RequestTime()
    ammo = open(os.path.join(path_to_ammo, "ammo", ammo_name), "r")
    with open(os.path.join(path_to_ammo, "answers", answer_name),
              "r") as answer:
        for answer_line in answer.readlines():
            # The typical request from ammo file during POST phase:
            #
            # 746 POST:/accounts/<id>/
            # POST /accounts/7316/?query_id=500 HTTP/1.1
            # Host: accounts.com
            # User-Agent: Technolab/1.0 (Docker; CentOS) Highload/1.0
            # Accept: */*
            # Connection: close
            # Content-Length: 536
            # Content-Type: application/json
            #
            # {...}

            # Skip the first line "746 POST:/accounts/<id>/"
            ammo.readline()

            # Read the second line and compare it with the appropriate line
            # from the answ file to be sure that we check corresponding
            # requets and answers. Just simple sanity check.
            req_line = ammo.readline().strip()
            request, expected_response_code, expected_response_body = (
                get_expected_results(answer_line))
            if (req_line.split(" ")[1] != request):
                print("FATAL: request/answer mismatch")
                print("Request: {}".format(req_line))
                print("Response: {}".format(answer_line))
                exit(1)

            # Read through the next header lines.
            for _ in range(0, 6):
                header_line = ammo.readline().strip()
                if header_line.startswith("Content-Length:"):
                    _, content_length = header_line.split(" ")
            ammo.readline()  # empty line after header
            payload = ""
            if content_length != "0":
                payload = ammo.readline().strip()

            before = datetime.now()
            response = requests.post(host + request,
                                     headers=headers_post, data=payload)
            after = datetime.now()
            request_time.add(before, after)
            check_response(response, expected_response_code,
                           expected_response_body)

    ammo.close()
    request_time.print_time()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="http://localhost:8080")
    parser.add_argument("--ammo_dir",
                        help="Path to the root dir with ammo and answers.")
    parser.add_argument("--all", action="store_true",
                        help="Run all three phases in series, default action.")
    parser.add_argument("--phase1", action="store_true",
                        help="Run phase 1.")
    parser.add_argument("--phase2", action="store_true",
                        help="Run phase 2.")
    parser.add_argument("--phase3", action="store_true",
                        help="Run phase 3.")
    parser.add_argument("--ignore_results", action="store_true", default=False,
                        help="Do not check answers from the server.")

    args = parser.parse_args()
    if not args.ammo_dir:
        print("ERROR: You have to specify the path to ammo!\n")
        parser.print_help()
        exit(1)
    if args.all and (args.phase1 or args.phase2 or args.phase3):
        print("ERROR: --all and --phaseX are mutually exclusive!\n")
        parser.print_help()
        exit(1)
    if not (args.phase1 or args.phase2 or args.phase3):
        args.all = True
    if args.all:
        args.phase1 = args.phase2 = args.phase3 = True

    host = args.host
    path_to_ammo = args.ammo_dir
    ignore_results = args.ignore_results

    if args.phase1:
        check_get('phase_1_get.answ')
    if args.phase2:
        check_post('phase_2_post.ammo', 'phase_2_post.answ')
    if args.phase3:
        check_get('phase_3_get.answ')
