import threading
import json
import logging
import re
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

from VeriFix_RLHF.data import write_jsonl, read_data
from VeriFix_RLHF.client import OpenAI_Client
from VeriFix_RLHF.multi_task import task_manager, add_task, worker

# 全局写入锁
write_lock = threading.Lock()

# 载入数据
raw_datas = read_data("./data/raw_data.jsonl")
print(f"Loaded {len(raw_datas)} raw data entries.")
# print("Sample data:", raw_datas[0]["text"])

# 数据处理提示词
data_process_prompt = """
请你根据我的 Verilog 代码生成出这个模块的描述，我想用这个描述给大模型提问来生成代码。同时也给我模块的头部信息包括模块名称和输入输出。

要求：
1. 模块描述：清晰描述模块的功能、输入输出端口的作用以及工作逻辑。
2. 模块头部信息：包括模块名称、输入输出端口及其位宽，使用 Verilog 语法。注意！！！：请不要给完整的代码，我只要头部信息
3. 不要擅自修改模块头部信息和任何无关的其他信息，不要写任何注释，否则会导致大模型生成的代码无法正常工作。
4. 输出格式：JSON 格式，包含 description 和 module_header 两个字段。

输出格式示例：
```json
{
  "description": "该模块实现了一个同步 FIFO（First-In-First-Out）队列，用于在时钟信号的控制下存储和读取数据。FIFO 的深度和宽度可以通过参数化配置。模块支持写操作（`wr_en`）和读操作（`rd_en`），并提供了空标志（`empty`）和满标志（`full`）来指示 FIFO 的状态。",
  "module_header": "module sync_fifo #(
    parameter DATA_WIDTH = 8,  // 数据位宽
    parameter FIFO_DEPTH = 16  // FIFO 深度
    )(
        input wire clk,            // 时钟信号
        input wire rst_n,          // 异步复位信号，低电平有效
        input wire wr_en,          // 写使能信号
        input wire rd_en,          // 读使能信号
        input wire [DATA_WIDTH-1:0] data_in, // 输入数据
        output reg [DATA_WIDTH-1:0] data_out, // 输出数据
        output wire empty,         // FIFO 空标志
        output wire full           // FIFO 满标志
    );"
}  
```
请根据以下 Verilog 代码生成描述和模块信息：
"""

def generate_one_completion(prompt):
    """
    调用 OpenAI API 生成结构化数据，返回包含 description 和 module_header 的字典
    """
    try:
        # 调用 OpenAI API（强制要求 JSON 格式）
        response = OpenAI_Client.chat.completions.create(
            model='gpt-4o-mini',
            messages=[
                {"role": "system", "content": "You are a helpful data processing assistant."},
                {"role": "user", "content": data_process_prompt + prompt}
            ],
            response_format={"type": "json_object"}  # 关键：强制JSON输出
        )
        raw_output = response.choices[0].message.content
        
        # 解析JSON
        result = json.loads(raw_output)
        
        # 提取字段（带默认值防错）
        description = result.get("description", "").strip()
        print("description: ", description)
        module_header = result.get("module_header", "").strip()
        print("module_header: ", module_header)

        # 验证模块头部是否包含关键语法
        if not module_header.startswith("module "):
            logging.warning(f"模块头部格式异常: {module_header[:50]}...")
            module_header = ""  # 置空错误数据

        return {
            "description": description,
            "module": module_header
        }
        
    except json.JSONDecodeError:
        logging.error("大模型返回了非JSON内容！原始输出:\n" + raw_output)
        return {"description": "", "module": ""}
    except KeyError as e:
        logging.error(f"JSON字段缺失: {e}")
        return {"description": "", "module": ""}
    except Exception as e:
        logging.error(f"API调用失败: {str(e)}")
        return {"description": "", "module": ""}

# 任务处理函数
def handler(extra_info):
    task_id = extra_info[0]
    prompt = extra_info[1]
    result = generate_one_completion(prompt)

    module_header = result["module"]
    match = re.search(r'module\s+([a-zA-Z0-9_]+)', module_header)  # 关键正则
    if not match:
        print(f"Task {task_id} 错误：无法提取模块名")
        return
    
    module_name = match.group(1)
    
    # 过滤逻辑：以 tb_ 开头或以 _tb 结尾的模块
    if module_name.startswith("tb_") or module_name.endswith("_tb"):
        print(f"Task {task_id} 被过滤（测试模块: {module_name}）")
        return
    
    description_samples = [dict(task_id=task_id, completion=result["description"])]
    module_samples = [dict(task_id=task_id, completion=result["module"])]
    # 带锁的写入操作
    with write_lock:
        write_jsonl("./data/Verilog_Description_v1.jsonl", description_samples, True)
        write_jsonl("./data/Verilog_Module_v1.jsonl", module_samples, True)
    print(f"Task {task_id} completed.")

# 并发控制
def main():
    #加载已有数据
    #如果存在Verilog_Module_v1.jsonl文件，则读取其中的数据
    try:
        with open('./data/Verilog_Module_v1.jsonl', 'r') as f:
            existing_data = [json.loads(line) for line in f]
    except FileNotFoundError:
        existing_data = []
    #去除掉existing_data中completion为空的数据
    existing_data = [sample for sample in existing_data if sample["completion"] != ""]
    #存储已经完成的任务的任务id
    finished_tasks = set(sample["task_id"] for sample in existing_data)
    print("已经完成了",finished_tasks)
    # 访问方式示例说明
    # print(existing_data[0])   
    # print(existing_data[0]["task_id"])
    # print(existing_data[0]["completion"])

    # 添加任务
    for i, data in enumerate(raw_datas):
        if i>=30:
            break
        # 跳过已经完成的任务
        if i in finished_tasks:
            continue
        add_task(str(i), [], [i, data["text"]])

    
    # 启动20个线程并发完成任务
    threads = [threading.Thread(target=worker, args=(task_manager, i, handler)) for i in range(20)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    # 使用线程池并发处理任务
    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = [executor.submit(worker, task_manager, i, handler) for i in range(20)]
        for future in futures:
            future.result()  # 等待所有任务完成

if __name__ == "__main__":
    main()