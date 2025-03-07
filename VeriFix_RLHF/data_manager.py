from .data import read_data
from collections import defaultdict

class VerilogDataManager:
    def __init__(self, base_path="./data/", version="v2"):
        # 初始化数据存储结构
        self.datasets = {
            "description": defaultdict(str),
            "definition": defaultdict(str),
            "code": defaultdict(str),
            "think": defaultdict(str)
        }
        
        # 加载处理后的统一数据
        self._load_data(f"{base_path}Verilog_Description_{version}.jsonl", "description")
        self._load_data(f"{base_path}Verilog_Definition_{version}.jsonl", "definition")
        self._load_data(f"{base_path}Verilog_R1_Code_{version}.jsonl", "code")
        self._load_data(f"{base_path}Verilog_R1_Think_{version}.jsonl", "think")

    def _load_data(self, file_path, dataset_name):
        """数据加载内部方法"""
        try:
            for item in read_data(file_path):
                task_id = item["task_id"]
                completion = item.get("completion", "")
                self.datasets[dataset_name][task_id] = completion
        except Exception as e:
            print(f"加载 {file_path} 失败: {str(e)}")

    def get_completions(self, task_id):
        """获取指定task_id的所有关联数据"""
        return {
            "description": self.datasets["description"].get(task_id, None),
            "definition": self.datasets["definition"].get(task_id, None),
            "code": self.datasets["code"].get(task_id, None),
            "think": self.datasets["think"].get(task_id, None)
        }

    def get_specific_completion(self, task_id, data_type):
        """获取指定类型的单个数据"""
        if data_type not in self.datasets:
            raise ValueError(f"无效的数据类型，可选：{list(self.datasets.keys())}")
        return self.datasets[data_type].get(task_id, None)
    
# 使用示例
if __name__ == "__main__":
    # 初始化数据管理器
    manager = VerilogDataManager(version="v2")
    
    # 示例查询
    sample_id = 53
    results = manager.get_completions(sample_id)
    
    print(f"=== Task {sample_id} 的完整数据 ===")
    for key, value in results.items():
        print(f"{key.upper()}:")
        print(value[:100] + "..." if value else "无数据")  # 限制输出长度

    # 单独获取某个类型
    code_content = manager.get_specific_completion(sample_id, "code")
    print("\n单独获取Code内容：")
    print(code_content[:200] if code_content else "无对应数据")