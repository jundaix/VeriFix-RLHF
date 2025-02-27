from typing import Iterable, Dict
import gzip
import json
import os


ROOT = os.path.dirname(os.path.abspath(__file__))

def read_problems(evalset_file: str) -> Dict[str, Dict]:
    return {task["task_id"]: task for task in stream_jsonl(evalset_file)}

def read_data(evalset_file: str) -> Dict[str, Dict]:
    return [data for data in stream_jsonl(evalset_file)] 

def stream_jsonl(filename: str) -> Iterable[Dict]:
    """
    逐行解析JSONL文件，并将每一行作为字典返回。
    
    :param filename: JSONL文件的路径
    :return: 一个生成器，每次生成一个字典
    """
    if filename.endswith(".gz"):  # 如果文件是gzip压缩的
        with open(filename, "rb") as gzfp:  # 以二进制模式打开文件
            with gzip.open(gzfp, 'rt', encoding='utf-8') as fp:  # 使用gzip解压文件，并以文本模式读取，指定编码为UTF-8
                for line in fp:  # 逐行读取文件
                    if any(not x.isspace() for x in line):  # 如果行中包含非空白字符
                        yield json.loads(line)  # 将JSON字符串解析为字典并返回
    else:  # 如果文件是普通文本文件
        with open(filename, "r", encoding='utf-8') as fp:  # 以文本模式打开文件，指定编码为UTF-8
            for line in fp:  # 逐行读取文件
                if any(not x.isspace() for x in line):  # 如果行中包含非空白字符
                    yield json.loads(line)  # 将JSON字符串解析为字典并返回


def write_jsonl(filename: str, data: Iterable[Dict], append: bool = False):
    """
    Writes an iterable of dictionaries to jsonl
    Skipping None in data
    """
    if append:
        mode = 'ab'
    else:
        mode = 'wb'
    filename = os.path.expanduser(filename)
    if filename.endswith(".gz"):
        with open(filename, mode) as fp:
            with gzip.GzipFile(fileobj=fp, mode='wb') as gzfp:
                for x in data:
                    if x:
                        gzfp.write((json.dumps(x) + "\n").encode('utf-8'))
    else:
        with open(filename, mode) as fp:
            for x in data:
                if x:
                    fp.write((json.dumps(x) + "\n").encode('utf-8'))