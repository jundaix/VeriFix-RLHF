import json
from VeriFix_RLHF.data import write_jsonl, read_data

from VeriFix_RLHF.data_manager import VerilogDataManager
# 读取输入数据
desc_data = read_data('./data/Verilog_Description_v2.jsonl')
defn_data = read_data('./data/Verilog_Definition_v2.jsonl')

# 读取输出数据
think_data = read_data('./data/Verilog_R1_Think_v2.jsonl')
code_data = read_data('./data/Verilog_R1_Code_v2.jsonl')

# 载入数据
data_manager = VerilogDataManager(version="v2")

# 验证数据一致性
assert len(desc_data) == len(defn_data) == len(think_data) == len(code_data), "文件行数不一致"

# 生成最终数据集
dataset = []
for idx in range(len(desc_data)):    
    # 构建instruction
    instruction = (
        f"模块描述：{desc_data[idx]['completion']}\n"
        f"模块定义：{defn_data[idx]['completion']}\n"
        "请你基于模块描述和定义，补全剩余代码，补全的代码中不要输出定义部分内容，"
        "但是要用verilog格式输出，用endmodule结束。"
    )
    data = data_manager.get_completions(desc_data[idx]["task_id"])

    think = data["think"]
    code = data["code"]
    output = f"<think>{think}</think>\n\n{code}".strip()
    
    # 构建最终数据对象
    dataset.append({
        "instruction": instruction,
        "output": output
    })

# 保存为JSON文件
with open('./data/formatted_dataset.json', 'w', encoding='utf-8') as f:
    json.dump(dataset, f, ensure_ascii=False, indent=2, sort_keys=False)

print(f"生成完成！共处理{len(dataset)}条数据")
print("输出文件路径：./data/formatted_dataset.json")