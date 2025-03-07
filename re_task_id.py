from VeriFix_RLHF.data import write_jsonl, read_data

def unify_task_ids(desc_path, code_path, think_path):
    # 载入所有数据
    description_data = read_data(desc_path)
    code_data = read_data(code_path)
    think_data = read_data(think_path)
    
    # 创建从行号到task_id的映射（从Description文件）
    line_to_task_id = [item["task_id"] for item in description_data]
    
    # 统一Code数据的task_id
    for code_item in code_data:
        original_task_id = code_item["task_id"]
        code_item["task_id"] = line_to_task_id[original_task_id]
    
    # 统一Think数据的task_id
    for think_item in think_data:
        original_task_id = think_item["task_id"]
        think_item["task_id"] = line_to_task_id[original_task_id]
    
    return code_data, think_data

# 使用示例
if __name__ == "__main__":
    # 输入文件路径
    desc_path = "./data/Verilog_Description_v2.jsonl"
    code_path = "./data/Verilog_R1_Code_v2.jsonl"
    think_path = "./data/Verilog_R1_Think_v2.jsonl"
    
    # 执行统一操作
    new_code_data, new_think_data = unify_task_ids(desc_path, code_path, think_path)
    
    # 保存结果（这里示例保存到v2版本，可根据需要修改）
    write_jsonl("./data/Verilog_R1_Code_v2.jsonl", new_code_data)
    write_jsonl("./data/Verilog_R1_Think_v2.jsonl", new_think_data)
    write_jsonl("./data/Verilog_R1_Code_v3.jsonl", new_code_data)
    write_jsonl("./data/Verilog_R1_Think_v3.jsonl", new_think_data)
    
    print(f"统一后的Code数据量：{len(new_code_data)}")
    print(f"统一后的Think数据量：{len(new_think_data)}")