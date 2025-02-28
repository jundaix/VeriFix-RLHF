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
请你根据我的 Verilog 代码生成出这个模块的描述和模块的定义，我想用这个模块描述和定义给大模型提问来生成代码。同时也整理提取一下我提供代码中的实现部分，我还想收集一下标准答案。

要求：
1. 模块描述：清晰描述模块的功能、输入输出端口的作用以及工作逻辑。
2. 模块定义：包括模块名称、输入输出端口及其位宽，使用 Verilog 语法。注意！！！：请不要给完整的代码，我只要定义信息
3. 模块实现：除了模块定义信息外的其他剩余代码
4. 不要擅自修改模块头部信息和模块实现以及任何无关的其他信息，不要写任何注释，否则会导致大模型生成的代码无法正常工作。
5. 输出格式：JSON 格式，包含 description、module_definition、module_code 三个字段。

输出格式示例：
```json
{
  "description": "该模块实现了一个同步 FIFO（First-In-First-Out）队列，用于在时钟信号的控制下存储和读取数据。FIFO 的深度和宽度可以通过参数化配置。模块支持写操作（`wr_en`）和读操作（`rd_en`），并提供了空标志（`empty`）和满标志（`full`）来指示 FIFO 的状态。",
  "module_definition": "module fifo #(
        parameter DATA_WIDTH = 8,
        parameter FIFO_DEPTH = 16
    )(
        input wire clk,
        input wire rst_n,
        input wire wr_en,
        input wire rd_en,
        input wire [DATA_WIDTH-1:0] data_in,
        output wire [DATA_WIDTH-1:0] data_out,
        output wire full,
        output wire empty
    );"
   "module_code": "    
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
" 
}  
```
请根据以下 Verilog 代码生成模块描述、模块定义、除模块定义部分外的模块实现代码：
"""

def generate_one_completion(prompt):
    """
    调用 OpenAI API 生成结构化数据，返回包含 description、module_definition 的字典。
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
        #print("description: ", description)
        module_definition = result.get("module_definition", "").strip()
        #print("module_definition: ", module_definition)
        module_code = result.get("module_code", "").strip()
        #print("module_code: ", module_code)


        # 验证模块头部是否包含关键语法
        if not module_definition.startswith("module "):
            logging.warning(f"模块头部格式异常: {module_definition[:50]}...")
            module_definition = ""  # 置空错误数据
            module_code = ""  # 置空错误数据
        # 验证模块实现代码是否以endmodule结尾
        if not module_code.lower().endswith("endmodule"):
            logging.warning(f"模块实现代码未结束: {module_code[:50]}...")
            module_code = ""  # 置空错误数据
            module_definition = ""  # 置空错误数据

        return {
            "description": description,
            "module_definition": module_definition,
            "module_code": module_code
        }
        
    except json.JSONDecodeError:
        logging.error("大模型返回了非JSON内容！原始输出:\n" + raw_output)
        return {"description": "", "module_definition": ""}
    except KeyError as e:
        logging.error(f"JSON字段缺失: {e}")
        return {"description": "", "module_definition": ""}
    except Exception as e:
        logging.error(f"API调用失败: {str(e)}")
        return {"description": "", "module_definition": ""}

# 任务处理函数
def handler(extra_info):
    task_id = extra_info[0]
    prompt = extra_info[1]
    result = generate_one_completion(prompt)
    
    ####################################过滤掉测试模块###############################
    module_definition = result["module_definition"]
    module_code = result["module_code"]
    match = re.search(r'module\s+([a-zA-Z0-9_]+)', module_definition)  # 关键正则
    if not match:
        print(f"Task {task_id} 错误：无法提取模块名")
        return
    
    module_name = match.group(1)
    
    # 过滤逻辑：以 tb_ 开头或以 _tb 结尾的模块
    if module_name.startswith("tb_") or module_name.endswith("_tb"):
        print(f"Task {task_id} 被过滤（测试模块: {module_name}）")
        bad_samples = [dict(task_id=task_id, completion="")]
        with write_lock:
            write_jsonl("./data/Verilog_Bad_Samples_v1.jsonl", bad_samples, True)
        return   
    # 过滤逻辑2： module代码中包含initial关键字的模块
    if "initial" in module_code:
        print(f"Task {task_id} 被过滤（含有初始化代码: {module_name}）")
        bad_samples = [dict(task_id=task_id, completion="")]
        with write_lock:
            write_jsonl("./data/Verilog_Bad_Samples_v1.jsonl", bad_samples, True)
        return
    # 过滤逻辑3： module代码中包含test关键字的模块
    if "test" in module_code:
        print(f"Task {task_id} 被过滤（含有测试代码: {module_name}）")
        bad_samples = [dict(task_id=task_id, completion="")]
        with write_lock:
            write_jsonl("./data/Verilog_Bad_Samples_v1.jsonl", bad_samples, True)
        return
    # 过滤逻辑4： 模块定义中包含test关键字的模块
    if "test" in module_definition:
        print(f"Task {task_id} 被过滤（含有test关键字: {module_name}）")
        bad_samples = [dict(task_id=task_id, completion="")]
        with write_lock:
            write_jsonl("./data/Verilog_Bad_Samples_v1.jsonl", bad_samples, True)
        return

    ################################################################################

    ###################################过滤掉此次内容为空生成失败的####################
    if module_definition == "":
        print(f"Task {task_id} 错误：生成格式出现了问题,跳过不写入")
        return
    ################################################################################
    
    description_samples = [dict(task_id=task_id, completion=result["description"])]
    definition_samples = [dict(task_id=task_id, completion=result["module_definition"])]
    code_samples = [dict(task_id=task_id, completion=result["module_code"])]
    # 带锁的写入操作
    with write_lock:
        write_jsonl("./data/Verilog_Description_v1.jsonl", description_samples, True)
        write_jsonl("./data/Verilog_Definition_v1.jsonl", definition_samples, True)
        write_jsonl("./data/Verilog_Code_v1.jsonl", code_samples, True)
    print(f"Task {task_id} completed.")

# 并发控制
def main():
    #加载已有数据
    #如果存在Verilog_Module_v1.jsonl文件，则读取其中的数据
    try:
        with open('./data/Verilog_Definition_v1.jsonl', 'r') as f:
            existing_data = [json.loads(line) for line in f]
    except FileNotFoundError:
        existing_data = []
    try:
        with open('./data/Verilog_Bad_Samples_v1.jsonl', 'r') as f:
            bad_data = [json.loads(line) for line in f]
    except FileNotFoundError:
        bad_data = []
    #去除掉existing_data中completion为空的数据
    existing_data = [sample for sample in existing_data if sample["completion"] != ""]
    #存储已经完成的任务的任务id
    finished_tasks = set(sample["task_id"] for sample in existing_data)
    print("已经完成了",finished_tasks)
    failed_tasks = set(sample["task_id"] for sample in bad_data)

    # 访问方式示例说明
    # print(existing_data[0])   
    # print(existing_data[0]["task_id"])
    # print(existing_data[0]["completion"])

    # 添加任务
    for i, data in enumerate(raw_datas):
        # 跳过已经完成的和失败的任务
        if (i in finished_tasks) or (i in failed_tasks):
            continue
        add_task(str(i), [], [i, data["text"]])

    
    # # 启动100个线程并发完成任务
    # threads = [threading.Thread(target=worker, args=(task_manager, i, handler)) for i in range(100)]
    # for thread in threads:
    #     thread.start()
    # for thread in threads:
    #     thread.join()

    # 使用线程池并发处理任务
    with ThreadPoolExecutor(max_workers=200) as executor:
        futures = [executor.submit(worker, task_manager, i, handler) for i in range(200)]
        for future in futures:
            future.result()  # 等待所有任务完成

if __name__ == "__main__":
    main()