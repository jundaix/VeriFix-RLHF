import json

def delete_task_id(task_id, filename):
    """
    从文件中删除指定任务ID的记录。
    
    Args:
        task_id (str): 需要删除的任务ID。
        filename (str): 包含任务记录的文件名。
    
    Returns:
        None
    
    Raises:
        FileNotFoundError: 如果指定的文件不存在。
    """
    with open(filename, 'r') as file:
        lines = file.readlines()
    
    filtered_lines = []
    for line in lines:
        try:
            data = json.loads(line.strip())
            if data.get('task_id') != task_id:
                filtered_lines.append(line)
        except json.JSONDecodeError:
            filtered_lines.append(line)
    with open(filename, 'w') as file:
        file.writelines(filtered_lines)
# id = "93"
# delete_task_id(int(id), "./data/111.jsonl")
# delete_task_id(93, "./data/111.jsonl")

#删除指定行的数据
def delete_line_number(line_number, filename):
    """
    从文件中删除指定行号的记录。
    
    Args:
        line_number (int): 需要删除的行号，从0开始。
        filename (str): 包含任务记录的文件名。
    
    Returns:
        None
    
    Raises:
        FileNotFoundError: 如果指定的文件不存在。
        ValueError: 如果行号无效（负数或超过文件最大行号）。
    """
    with open(filename, 'r') as file:
        lines = file.readlines()
    
    # 检查行号是否在有效范围内
    max_line = len(lines) - 1
    if line_number < 0 or line_number > max_line:
        raise ValueError(f"行号 {line_number} 无效，有效范围为 0 到 {max_line}")
    
    # 生成排除指定行号的新列表
    new_lines = [line for idx, line in enumerate(lines) if idx != line_number]
    
    with open(filename, 'w') as file:
        file.writelines(new_lines)
# id = "19"
# delete_line_number(int(id), "./data/111.jsonl")
# delete_line_number(93, "./data/111.jsonl")

def delete_all(task_id):
    delete_task_id(task_id, "./data/Verilog_Definition_v2.jsonl")
    delete_task_id(task_id, "./data/Verilog_Description_v2.jsonl")
    delete_task_id(task_id, "./data/Verilog_R1_Code_v2.jsonl")
    delete_task_id(task_id, "./data/Verilog_R1_Think_v2.jsonl")

    #删除掉了描述和定义的task_id那一行
    print(f"删除描述和定义中的R1数据的task_id:{task_id}的那一行")

        


