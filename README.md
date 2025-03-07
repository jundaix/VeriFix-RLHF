# VeriFix-RLHF 项目文档

## 项目概述
本项目用于自动化处理 Verilog 代码，通过调用大模型 API 生成模块的功能描述和头部信息，支持多线程并发处理以提高效率。生成的描述和模块信息将保存为 JSONL 格式文件，可用于后续代码生成或验证任务。

---

## 功能特性
- **自动化解析**：根据 Verilog 代码生成模块描述和头部信息
- **多线程处理**：支持 20 线程并发处理任务
- **数据过滤**：自动过滤测试模块（以 `tb_` 开头或 `_tb` 结尾的模块）
- **断点续传**：支持从已处理任务中恢复，避免重复处理

---

## 环境配置

### 依赖安装
```bash
conda create -n VeriFix-RLHF python=3.9
conda activate VeriFix-RLHF
pip install -r requirements.txt
```



## 使用方法

### 数据准备

将需要处理的 Verilog 代码按以下格式存入 `data/raw_data.jsonl`：

```json
{"text": "module example (...) ..."}
{"text": "module another_module (...) ..."}
```



## 运行处理程序

bash

```bash
python data_process.py
```

## 输出结果

- 描述文件：`data/Verilog_Description_v1.jsonl`
- 模块头部文件：`data/Verilog_Module_v1.jsonl`

示例输出条目：

```json
{
  "task_id": "0",
  "completion": "module sync_fifo #(...)(...);"
}
```

## 高级配置

### 并发控制

修改 `data_process.py` 中的线程数（默认 20 线程）：

```python
# 启动线程数
threads = [threading.Thread(...) for i in range(20)]
```

### 处理限制

默认处理前 30 条数据，修改以下代码调整：

```python
for i, data in enumerate(raw_datas):
    if i >= 30:  # 修改此数值
        break
```

## 注意事项

- **API 可用性**：确保 API 密钥有效且配额充足

- **输入格式**：原始数据必须包含有效的 Verilog 模块定义

- 

  错误处理

  ：查看日志文件排查以下问题：

  - 模块头部语法不符合规范
  - API 返回非 JSON 格式内容
  - 网络连接异常

- **硬件要求**：建议 4GB+ 内存环境运行多线程任务

## 示例场景

假设 `raw_data.jsonl` 包含：

```json
{"text": "module adder (input [3:0] a, b, output [4:0] sum); assign sum = a + b; endmodule"}
```

运行后将生成：

```json
// Verilog_Description_v1.jsonl
{"task_id": "0", "completion": "该模块实现了一个4位加法器..."}

// Verilog_Module_v1.jsonl 
{"task_id": "0", "completion": "module adder (input [3:0] a, b, output [4:0] sum);"}
```