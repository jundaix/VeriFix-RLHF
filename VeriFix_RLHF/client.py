from openai import OpenAI
from dotenv import load_dotenv
import os

# 加载 .env 文件中的环境变量
load_dotenv()

OpenAI_API_KEY = os.getenv("OPENAI_API_KEY")
DeepSeek_Douyin_API_KEY = os.getenv("DEEPSEEK_DOUYIN_API_KEY")

DS_Douyin_client = OpenAI(
    api_key = DeepSeek_Douyin_API_KEY,
    base_url = "https://ark.cn-beijing.volces.com/api/v3",
)

OpenAI_Client = OpenAI(
    api_key = OpenAI_API_KEY,
    base_url = 'https://xiaoai.plus/v1',
)