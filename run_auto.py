import json, gc, re
from raptor import RetrievalAugmentation, RetrievalAugmentationConfig, SBertEmbeddingModel
from localllm import QwenSummarizationModel, QwenQAModel

def extract_final_answer(s):
    # 找到最后一个"assistant\n"出现的位置
    last_assistant_pos = s.rfind('assistant\n')
    if last_assistant_pos == -1:
        return ""  # 未找到"assistant\n"部分
    
    # 获取从该位置之后的子字符串
    substring = s[last_assistant_pos+10:]
    return substring.strip()  # 去除前后空格


def raptor_init() -> RetrievalAugmentation:
    """
    初始化 Raptor 模型。
    """
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
    return RA

def call_raptor(question: str, context: str) -> str:
    """
    调用 Raptor ，返回预测答案。
    """
    RA = raptor_init()
    RA.add_documents(context)  # 添加上下文
    raw_answer = RA.answer_question(question=question)  # 提问
    answer = extract_final_answer(raw_answer)  # 提取答案
    del RA  # 清理内存
    gc.collect()  # 强制垃圾回收

    return answer

def normalize_answer(answer: str) -> str:
    """标准化答案格式（转小写、去标点、去空格）"""
    return answer.strip().lower().replace(".", "").replace(" ", "")

def evaluate_dataset(file_path: str) -> None:
    correct = 0
    total = 0
    
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            # 逐行读取并解析每个 JSON 对象
            try:
                entry = json.loads(line.strip())
            except json.JSONDecodeError as e:
                print(f"Error parsing line: {line[:50]}... | Error: {str(e)}")
                continue  # 跳过解析失败的行
            
            idx = entry.get("idx", "N/A")
            question = entry.get("question", "")
            context = entry.get("context", "")
            targets = entry.get("targets", [])
            
            # 调用 Raptor 模型获取预测答案
            prediction = call_raptor(question, context)
            
            # 标准化答案
            normalized_prediction = normalize_answer(prediction)
            normalized_targets = [normalize_answer(t) for t in targets]

            # 调试输出：
            print(f"Model Prediction: {prediction}")
            print(f"Normalized Prediction: {normalized_prediction}")
            print(f"Targets: {targets}")
            print(f"Normalized Targets: {normalized_targets}")
            # 判断是否正确
            # is_correct = normalized_prediction in normalized_targets
            is_correct = any(target in normalized_prediction for target in normalized_targets)
            if is_correct:
                correct += 1
            total += 1
            
            # 打印详细信息（可选）
            print(f"ID: {idx}")
            print(f"Question: {question}")
            print(f"Prediction: {prediction} → {'Correct' if is_correct else 'Incorrect'}")
            print(f"Targets: {targets}\n")
    
    # 输出最终准确率
    accuracy = correct / total if total != 0 else 0
    print(f"Total: {total}, Correct: {correct}, Accuracy: {accuracy:.2%}")

if __name__ == "__main__":
    evaluate_dataset("partial_test_easy.jsonl")