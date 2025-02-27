import json
import os
file_name = "Verilog_Module_v1.jsonl"
with open(file_name, "r", encoding='utf-8') as fp:
    for line in fp:
        data = json.loads(line)
        print(data["completion"])

file_name = "Verilog_Description_v1.jsonl"
with open(file_name, "r", encoding='utf-8') as fp:
    for line in fp:
        data = json.loads(line)
        print(data["completion"])