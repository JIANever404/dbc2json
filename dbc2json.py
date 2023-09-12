#!/usr/bin/python3

# Script to convert a Vector CANoe ".dbc" file in the right JSON format for Automotive Grade Linux (AGL), this software is currently a feasibility study.
# Created on 16th May 2020 by walzert version 0.1 
# The Python3 requirements are noted in requirements.txt.
# The software is based on cantools: https://github.com/eerimoq/cantools.
# It converts messages from a dbc file (-i input) and adds the data header for AGL on top of the messages.

import sys
import getopt
import os
import cantools
import json

with open("{}/header.json".format(os.path.dirname(os.path.realpath(__file__)))) as json_file:
    data_header = json.load(json_file)

messages_list = []

def usage():
    usage = """dbc2json.py [ -i | --in ] [ -o | --out ] [ -v | --version ] [ -p || --prefix ] [ -b | --bus ] [ -m | --mode ] [ -j | --j1939 ] [ -f | --fd ] [ -r | --reversed ] [ -e | --big-endian ] [ -l | --little-endian ] [ -h | --help ]
    - in: input file (.dbc) [MANDATORY]
    - out: output file (.json)
    - prefix: message's name prefix
    - version: signals version
    - bus: bus name
    - mode: signal is writable
    - j1939: signals used j1939
    - fd: signals used FD
    - reversed: bits position are reversed
    - big-endian: bytes position are reversed
    - little-endian: self-explanatory"""
    error(usage)

def error(err: str):
    print(err)
    sys.exit(1)

def formatName(name: str):
    return name.replace("_", ".")

def main(argv):
    inputfile = None
    outputfile = None
    prefix = None
    version = "0.0"
    bus = None
    mode = False
    j1939 = False
    fd = False
    rev = False
    bigE = False
    litE = False
    try:
        opts, args = getopt.getopt(argv, "i:o:p:v:b:wjfrelh", ["in", "out", "prefix", "version", "bus", "mode", "j1939", "fd", "reversed", "big-endian", "little-endian", "help"])
    except getopt.GetoptError:
        usage()
    for opt, arg in opts:
        if opt in ("-h", "--help"):
            usage()
        elif opt in ("-i", "--in"):
            inputfile = arg.strip()
        elif opt in ("-o", "--out"):
            outputfile = arg.strip()
        elif opt in ("-p", "--prefix"):
            prefix = arg.strip()
        elif opt in ("-v", "--version"):
            version = arg.strip()
        elif opt in ("-b", "--bus"):
            bus = arg.strip()
        elif opt in ("-w", "--writeable"):
            mode = True
        elif opt in ("-j", "--j1939"):
            j1939 = True
        elif opt in ("-f", "--fd"):
            fd = True
        elif opt in ("-r", "--reversed"):
            rev = True
        elif opt in ("-e", "--big-endian"):
            bigE = True
        elif opt in ("-l", "--little-endian"):
            litE = True

    if not inputfile:
        usage()
    if not inputfile.endswith(".dbc"):
        error("Wrong input file type (must be .dbc)")
    if not bus:
        bus = "hs"
    if bigE and litE:
        error("Little and big endian flag can't be used together")
    data_header["name"] = os.path.splitext(os.path.basename(inputfile))[0]
    data_header["version"] = version
    db = cantools.database.load_file(inputfile)
    for message in db.messages:
        # if prefix:
        #     message.name = "{}.{}".format(prefix, message.name)
        if bigE or litE or rev:
            message_json = {
                # "id": hex(message.frame_id),
                "id": message.frame_id,
                "name": message.name,
                "bus": bus,
                "length": message.length,
                "is_fd": fd,
                "is_j1939": j1939,
                "is_extended": message.is_extended_frame,
                "byte_frame_is_big_endian": bigE,
                "bit_position_reversed": rev,
                "signals": []
            }
        else:
            message_json = {
                # "id": hex(message.frame_id),
                "id": message.frame_id,
                "name": message.name,
                "bus": bus,
                "length": message.length,
                "is_fd": fd,
                "is_j1939": j1939,
                "is_extended": message.is_extended_frame,
                "signals": []
            }
        if message.cycle_time is not None and message.cycle_time > 0:
            message_json["max_frequency"] = 1000.0 / message.cycle_time
        hex_value = str(hex(message.frame_id))
        messages_list.append(message_json)
        signal_list = message_json["signals"]
        signals = message.signals

        for signal in signals:
            SName = signal
            # name = "{}.{}".format(formatName(message.name), formatName(signal.name))
            name = signal.name
            signal_json = {
                "name": name,
                # "generic_name": formatName(signal.name),
                "bit_position": signal.start,
                "bit_size": signal.length,
                "factor": signal.scale,
                "offset": signal.offset,
                "byte_order": signal.byte_order,
                "writable": mode
            }
            if message.cycle_time is not None and message.cycle_time > 0:
                signal_json["max_frequency"] = 1000.0 / message.cycle_time
            if signal.unit is not None:
                signal_json["unit"] = signal.unit
            if signal.minimum is not None:
                signal_json["min_value"] = signal.minimum
            if signal.maximum is not None:
                signal_json["max_value"] = signal.maximum
            if signal.is_multiplexer:
                signal_json["multiplexer"] = 'Multiplexor'
            if signal.multiplexer_ids:
                signal_json["multiplexer"] = signal.multiplexer_ids[0]
            signal_list.append(signal_json)

    output_all = data_header 
    output_all["messages"] = messages_list
    with open(outputfile, 'w') if outputfile else sys.stdout as outfile:
        json.dump(output_all, outfile, indent=4)
        outfile.write('\n')
    if outputfile:
        print("Finished")

if __name__ == '__main__':
    main(sys.argv[1:])
