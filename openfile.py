import json
import os
#此文件用于检测数据的编码是否可以被utf-8正常解析
# file_name = "Verilog_Module_v1.jsonl"
# with open(file_name, "r", encoding='utf-8') as fp:
#     for line in fp:
#         data = json.loads(line)
#         print(data["completion"])

# file_name = "Verilog_Description_v1.jsonl"
# with open(file_name, "r", encoding='utf-8') as fp:
#     for line in fp:
#         data = json.loads(line)
#         print(data["completion"])

file_name = "./data/Verilog_R1_Think_v1.jsonl"
with open(file_name, "r", encoding='utf-8') as fp:
    for line in fp:
        data = json.loads(line)
        print(data["completion"])