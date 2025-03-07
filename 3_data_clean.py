import threading
import json
import logging
import re
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

from VeriFix_RLHF.data import write_jsonl, read_data
from VeriFix_RLHF.client import OpenAI_Client
from VeriFix_RLHF.multi_task import task_manager, add_task, worker
from VeriFix_RLHF.data_manager import VerilogDataManager
from delete_task_id import delete_all
# 全局写入锁
write_lock = threading.Lock()

# 载入数据
data_manager = VerilogDataManager(version="v2")
code_datas = read_data("./data/Verilog_R1_Code_v2.jsonl")
print(f"Loaded {len(code_datas)} Code data entries.")

# 数据处理提示词
data_process_prompt = """请你分析判断我的Verilog代码中是否有语法错误，尤其是C语言和Verilog语言混用的情况，比如代码中使用了enum、typedef等这些属于C语言的语法，除了语法错误你也可以检查其他的错误。
并最终用如下格式返回：
<analyse> 分析过程</analyse>
<result>True or False</result>
其中False代表此代码有错误。
我的Verilog代码如下：{definition}\n{code}
"""

def generate_one_completion(prompt):
    """
    
    """
    # 调用 OpenAI API（强制要求 JSON 格式）
    response = OpenAI_Client.chat.completions.create(
        model='gpt-4o-mini',
        messages=[
            {"role": "system", "content": "You are an expert in evaluating Verilog code."},
            {"role": "user", "content": prompt}
        ],
    )
    raw_output = response.choices[0].message.content
    print(raw_output)
    return raw_output
        
# 任务处理函数
def handler(extra_info):
    line_number = extra_info[0]
    prompt = extra_info[1]
    #找到difinition的数据
    task_id = code_datas[line_number]["task_id"]
    # definition = data_manager.get_specific_completion(task_id=task_id,data_type="definition")
    # print("code: "+definition+"\n"+code_datas[line_number]["completion"])
    completion = generate_one_completion(prompt)
    # 解析结果
    try:
        result = re.search(r'(?<=<result>).*(?=<\/result>)', completion).group().strip()
    except AttributeError:
        result = ""

    #如果结果是False，则删除该任务id对应的数据
    if result == "False":
        with write_lock:
            #记录要删除的task_id到delete_log.txt中
            with open("./log/delete_log.txt", "a", encoding='utf-8') as f:
                f.write(str(task_id))
                f.write("\n")
                print(f"Task {task_id} deleted.")
            #将completion写入到log.jsonl文件中
            with open("./log/log.jsonl", "a",encoding='utf-8') as f:
                json.dump({"task_id": task_id,"completion":completion}, f, ensure_ascii=False)
                f.write("\n")
    print(f"Task {task_id} completed.")

# 并发控制
def main():
    # 添加任务
    for i, data in enumerate(code_datas):
        #找到difinition的数据
        definition = data_manager.get_specific_completion(task_id=data["task_id"],data_type="definition")
        # 构造prompt
        prompt = data_process_prompt.format(definition = definition ,code=code_datas[i]["completion"])
        add_task(str(i), [], [i,prompt])

    # 使用线程池并发处理任务
    with ThreadPoolExecutor(max_workers=200) as executor:
        futures = [executor.submit(worker, task_manager, i, handler) for i in range(200)]
        for future in futures:
            future.result()  # 等待所有任务完成

    #所有任务完成后，根据delete_log.txt的文件 删除所有task_id对应的数据
    with open('./log/delete_log.txt', 'r', encoding='utf-8') as file:
        lines = file.readlines()
        for line in lines:
            task_id = int(line.strip())
            delete_all(task_id = task_id)


if __name__ == "__main__":
    main()  