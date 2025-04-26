from raptor import RetrievalAugmentation, RetrievalAugmentationConfig, SBertEmbeddingModel
from localllm import QwenSummarizationModel, QwenQAModel
import json
SAVE_PATH = "./trees/Givanildo_Oliveira_&_Sabine_Hossenfelder"
# Initialize your custom models
custom_summarizer = QwenSummarizationModel()
custom_qa = QwenQAModel()
custom_embedding = SBertEmbeddingModel()

# Create a config with your custom models
custom_config = RetrievalAugmentationConfig(
    summarization_model=custom_summarizer,
    qa_model=custom_qa,
    embedding_model=custom_embedding,
)

# Initialize RAPTOR with your custom config
RA = RetrievalAugmentation(config=custom_config)
# # 解析JSON数据
with open('partial_dev_easy.json', 'r') as f:
    data = json.load(f)
# 合并所有条目中的paras内容
all_paragraphs = []
for entry in data:
    all_paragraphs.extend(entry.get("paras", []))

# 将段落用换行符连接成文档文本
document_text = '\n'.join(all_paragraphs)

# 添加文档到检索系统
RA.add_documents(document_text)

    



#开始提问
easy1=[
    "Givanildo Oliveira played for which team from 1969 to 1976?",
    "Givanildo Oliveira played for which team from 1976 to 1977?",
    "Givanildo Oliveira played for which team from 1977 to 1979?",
    "Givanildo Oliveira played for which team from 1980 to 1984?"
]
hard1=[
    "Which team did the player Givanildo Oliveira belong to in early 1970s?",
    "Which team did the player Givanildo Oliveira belong to between Mar 1976 and Sep 1976?",
    "Which team did the player Givanildo Oliveira belong to between Mar 1977 and Dec 1977?",
    "Which team did the player Givanildo Oliveira belong to after Feb 1982?"
]
easy2=[
    "Which American higher learning institution did German physicist Sabine Hossenfelder work from 2004 to 2005?",
    "At which California university did the author and physicist Sabine Hossenfelder work in 2005 to 2006?",
    "From 2006 to 2009, which Canadian institution employed Sabine Hossenfelder, a well known German physicist?"
]
for idx,question in enumerate(easy2):
    print(f"Question {idx + 1}:")
    print(question)
    answer = RA.answer_question(question=question)
    print("Answer: ", answer)
    print("\n---\n")

RA.save(SAVE_PATH)


