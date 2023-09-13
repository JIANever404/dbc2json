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
    signalIndex = 0
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
    db = cantools.database.load_file(inputfile,encoding='utf-8')
    for message in db.messages:
        # if prefix:
        #     message.name = "{}.{}".format(prefix, message.name)
        msg_max_frequency = 0.0
        if message.cycle_time is not None and message.cycle_time > 0:
            msg_max_frequency = message_json["msg_max_frequency"] = 1000.0 / message.cycle_time
        if bigE or litE or rev:
            message_json = {
                # "id": hex(message.frame_id),
                "canId": message.frame_id,
                "channelId": 1,
                "name": message.name,
                "bus": bus,
                "length": message.length,
                "is_fd": fd,
                "is_j1939": j1939,
                "is_extended": message.is_extended_frame,
                "byte_frame_is_big_endian": bigE,
                "bit_position_reversed": rev,
                "msg_max_frequency" : msg_max_frequency,
                "signals": []
            }
        else:
            message_json = {
                # "id": hex(message.frame_id),
                "canId": message.frame_id,
                "channelId": 1,
                "name": message.name,
                "bus": bus,
                "length": message.length,
                "is_fd": fd,
                "is_j1939": j1939,
                "is_extended": message.is_extended_frame,
                "msg_max_frequency" : msg_max_frequency,
                "signals": []
            }
        hex_value = str(hex(message.frame_id))
        messages_list.append(message_json)
        signal_list = message_json["signals"]
        signals = message.signals

        for signal in signals:
            SName = signal
            # name = "{}.{}".format(formatName(message.name), formatName(signal.name))
            name = signal.name
            signalIndex = signalIndex + 1
            signal_json = {
                "signalName": name,
                "signalIndex" : signalIndex,
                # "generic_name": formatName(signal.name),
                "startBit": signal.start,
                "length": signal.length,
                "factor": float(signal.scale),
                "offset": float(signal.offset),
                "byte_order": signal.byte_order,
                # "writable": mode
            }
            # print(type(signal.scale))
            # print(type(signal.offset))
            if message.cycle_time is not None and message.cycle_time > 0:
                signal_json["max_frequency"] = 1000.0 / message.cycle_time
            else:
                signal_json["max_frequency"] = 0.0
            if signal.unit is not None:
                signal_json["unit"] = signal.unit
            else:
                signal_json["unit"] = "none"
            if signal.minimum is not None:
                # print(type(signal.minimum))
                signal_json["min"] = float(signal.minimum)
            else:
                signal_json["min"] = 0.0
            if signal.maximum is not None:
                signal_json["max"] = float(signal.maximum)
                # print(type(signal.maximum))
            else:
                signal_json["max"] = 0.0
            if signal.is_multiplexer:
                signal_json["multiplexer"] = True
            else:
                signal_json["multiplexer"] = False
            if signal.multiplexer_ids:
                signal_json["multiplexer_ids"] = signal.multiplexer_ids
            else:
                signal_json["multiplexer_ids"] = []


            #判断信号val类型
            valtype="longlong"
            if any(isinstance(val, float) for val in [signal.scale, signal.offset, signal.minimum, signal.maximum]):
                #信号是一个float值
                # print("is float")
                valtype="float"
            else:
                #信号是一个整数值 至于是什么类型再继续细化
                # print("is not float")
                if signal.minimum is None or signal.maximum is None:
                    #最大值最小值缺失 无法判断类型 统一为long long
                    # print("is longlong")
                    valtype="int64"
                else:
                    #最大值最小值都存在 根据最大最小值进一步细化类型
                    if signal.minimum < 0:
                        #说明是有符号类型整数
                        if signal.minimum >= -128 and signal.maximum <= 127:
                            valtype="int8"
                        elif signal.minimum >= -32768 and signal.maximum <= 32767:
                            valtype="int16"
                        elif signal.minimum >= -2147483648 and signal.maximum <= 2147483647:
                            valtype="int32"
                        else:
                            valtype="int64"
                    else:
                        #正整数
                        if signal.maximum <= 255:
                            valtype="uint8"
                        elif signal.maximum <= 65535:
                            valtype="uint16"
                        elif signal.maximum <= 4294967295:
                            valtype="uint32"
                        else:
                            valtype="uint64"
            signal_json["value_type"] = valtype

            #取出dbc的信号枚举
            enum_values = signal.conversion.choices
            if enum_values is not None:
                # print(type(enum_values))
                enum_list = []
                for value, description in enum_values.items():
                    # print(type(value))
                    # print(value)
                    # print(type(description))
                    # print(description)
                    enum_dict = {
                        "name": description.name,
                        "value": description.value
                    }
                    enum_list.append(enum_dict)
                
                signal_json["enums"] = enum_list
            else:
                signal_json["enums"] = []

            

            signal_list.append(signal_json)

    output_all = data_header 
    data_json = {
        "canEncodeMode" : 1,
        "canItems" : messages_list
    }
    output_all["data"] = data_json
    with open(outputfile, 'w', encoding='utf-8') if outputfile else sys.stdout as outfile:
        json.dump(output_all, outfile, ensure_ascii=False, indent=4)
        outfile.write('\n')
    if outputfile:
        print("Finished")

if __name__ == '__main__':
    main(sys.argv[1:])
