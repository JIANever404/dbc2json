#!/usr/bin/bash

set -e

python3.10 dbc2json.py -i $1 > signal.json