import json

def delete_task_id(task_id, filename):
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

#(8,"/Users/zouxiaoyu/Desktop/Verilog_Bad_Samples_v1.jsonl")