import json
from raptor import RetrievalAugmentation
import sys
sys.path.append("..")
from os_init import set_openai_api_key

set_openai_api_key()

# Initialize with default configuration. For advanced configurations, check the documentation. [WIP]
RA = RetrievalAugmentation()

# 解析JSON数据
data = json.load(open('partial_data.json'))

# 获取paras字段中的所有语段
paragraphs = data.get("paras", [])

# 逐个读取并打印每个语段
for idx, para in enumerate(paragraphs):
    print(f"Paragraph {idx + 1}:")
    print(para)
    print("\n---\n")