import threading
import json
import logging
import re
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

from VeriFix_RLHF.data import write_jsonl, read_data
from VeriFix_RLHF.client import DS_Douyin_client
from VeriFix_RLHF.multi_task import task_manager, add_task, worker

# 全局写入锁
write_lock = threading.Lock()

# 载入数据
description_datas = read_data("./data/Verilog_Description_v1.jsonl")
print(f"Loaded {len(description_datas)} description data entries.")
definition_datas = read_data("./data/Verilog_Definition_v1.jsonl")
print(f"Loaded {len(definition_datas)} definition data entries.")
# print("Sample data:", raw_datas[0]["text"])

# 数据处理提示词
data_process_prompt = """
模块描述：{description}
模块定义：{module_definition}
请你基于模块描述和定义，补全剩余代码，补全的代码中不要输出定义部分内容，但是要用verilog格式输出，用endmodule结束。
示例输出：```verilog
        localparam ADDR_WIDTH = $clog2(FIFO_DEPTH);
        reg [DATA_WIDTH-1:0] mem [0:FIFO_DEPTH-1];
        reg [ADDR_WIDTH:0] wr_ptr;
        reg [ADDR_WIDTH:0] rd_ptr;
        reg [ADDR_WIDTH:0] ptr_diff;

        // FIFO 空/满标志
        assign empty = (wr_ptr == rd_ptr);
        assign full = (wr_ptr[ADDR_WIDTH-1:0] == rd_ptr[ADDR_WIDTH-1:0]) && (wr_ptr[ADDR_WIDTH] != rd_ptr[ADDR_WIDTH]);

        // 数据输出
        assign data_out = mem[rd_ptr[ADDR_WIDTH-1:0]];

        // 写操作
        always @(posedge clk or negedge rst_n) begin
            if (!rst_n) begin
                wr_ptr <= 0;
            end else if (wr_en && !full) begin
                mem[wr_ptr[ADDR_WIDTH-1:0]] <= data_in;
                wr_ptr <= wr_ptr + 1;
            end
        end

        // 读操作
        always @(posedge clk or negedge rst_n) begin
            if (!rst_n) begin
                rd_ptr <= 0;
            end else if (rd_en && !empty) begin
                rd_ptr <= rd_ptr + 1;
            end
        end

    endmodule
```
"""

def generate_one_completion(prompt):
    """
    根据给定的提示生成单个代码补全。
    
    Args:
        prompt (str): 用户输入的提示，作为生成代码补全的输入。
    
    Returns:
        dict: 包含生成的思考内容和代码补全的字典。
    
            - think_data (str): 生成代码补全过程中的思考内容。
            - module_code (str): 生成的代码补全。
    
    """
    # 调用 OpenAI API（强制要求 JSON 格式）
    response = DS_Douyin_client.chat.completions.create(
        model='deepseek-r1-250120',
        messages=[
            {"role": "user", "content": prompt}
        ],
        temperature=0.6
    )
    raw_think = response.choices[0].message.reasoning_content
    raw_output = response.choices[0].message.content
    
    return {
        "think_data": raw_think,
        "module_code": raw_output
    }
        
# 任务处理函数
def handler(extra_info):
    task_id = extra_info[0]
    prompt = extra_info[1]

    result = generate_one_completion(prompt)
    
    think_data = result["think_data"]
    module_code = result["module_code"]
    ####################################过滤掉测试模块###############################

        # 验证模块代码是否以module开头
    if module_code.startswith("module "):
        logging.warning(f"模块头部格式异常: {module_code[:50]}...")
        module_code = ""  # 置空错误数据
        think_data = ""  # 置空错误数据
    # 验证模块实现代码是否以endmodule\n```结尾
    if not module_code.lower().endswith("endmodule\n```"):
        logging.warning(f"模块实现代码未结束: {module_code[:50]}...")
        module_code = ""  # 置空错误数据
        think_data = ""  # 置空错误数据

    ################################################################################

    ###################################过滤掉此次内容为空生成失败的####################
    if module_code == "":
        print(f"Task {task_id} 错误：生成格式出现了问题,跳过不写入")
        return
    ################################################################################
    
    r1_think_data = [dict(task_id=task_id, completion=think_data)]
    r1_code_samples = [dict(task_id=task_id, completion=module_code)]
    # 带锁的写入操作
    with write_lock:
        write_jsonl("./data/Verilog_R1_Think_v1.jsonl", r1_think_data, True)
        write_jsonl("./data/Verilog_R1_Code_v1.jsonl", r1_code_samples, True)
    print(f"Task {task_id} completed.")

# 并发控制
def main():
    #加载已有数据
    #如果存在Verilog_Module_v1.jsonl文件，则读取其中的数据
    try:
        with open('./data/Verilog_R1_Think_v1.jsonl', 'r') as f:
            existing_data = [json.loads(line) for line in f]
    except FileNotFoundError:
        existing_data = []
    # try:
    #     with open('./data/Verilog_Bad_Samples_v1.jsonl', 'r') as f:
    #         bad_data = [json.loads(line) for line in f]
    # except FileNotFoundError:
    #     bad_data = []
    #去除掉existing_data中completion为空的数据
    existing_data = [sample for sample in existing_data if sample["completion"] != ""]
    #存储已经完成的任务的任务id
    finished_tasks = set(sample["task_id"] for sample in existing_data)
    print("已经完成了",finished_tasks)
    # failed_tasks = set(sample["task_id"] for sample in bad_data)

    # 访问方式示例说明
    # print(existing_data[0])   
    # print(existing_data[0]["task_id"])
    # print(existing_data[0]["completion"])

    # 添加任务
    for i, data in enumerate(description_datas):
        # 跳过已经完成的和失败的任务
        if (i in finished_tasks):
            continue
        # 构造prompt
        prompt = data_process_prompt.format(description=description_datas[i]["completion"], module_definition=definition_datas[i]["completion"])
        add_task(str(i), [], [i, prompt])

    # 使用线程池并发处理任务
    with ThreadPoolExecutor(max_workers=200) as executor:
        futures = [executor.submit(worker, task_manager, i, handler) for i in range(200)]
        for future in futures:
            future.result()  # 等待所有任务完成

if __name__ == "__main__":
    main()