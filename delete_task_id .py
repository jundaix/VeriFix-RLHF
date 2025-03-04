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