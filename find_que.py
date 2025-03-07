from VeriFix_RLHF.data import write_jsonl, read_data
def find_missing_task_ids(data):
    """
    找出缺失的task_id
    :param data: 包含所有JSON对象的列表
    :return: 缺失的task_id列表
    """
    task_ids = set()
    missing_task_ids = set()

    for obj in data:
        if 'task_id' in obj:
            task_id = obj['task_id']
            task_ids.add(task_id)
        else:
            # 如果对象中没有task_id字段，则视为缺失
            missing_task_ids.add(None)

    # 假设task_id是连续的，从0开始
    max_task_id = max(task_ids) if task_ids else 0
    all_task_ids = set(range(max_task_id + 1))

    # 找出缺失的task_id
    missing_task_ids.update(all_task_ids - task_ids)

    return sorted(missing_task_ids)

def main():
    # 载入数据
    file_path = "./data/Verilog_R1_Code_v2.jsonl"
    code_datas = read_data(file_path)

    # 找出缺失的task_id
    missing_task_ids = find_missing_task_ids(code_datas)

    # 输出结果
    print("缺失的task_id:", missing_task_ids)

if __name__ == "__main__":
    main()