import json
import gc
import sys
import datetime
import logging
import os
from raptor import RetrievalAugmentation, RetrievalAugmentationConfig, SBertEmbeddingModel
from localllm import QwenSummarizationModel, QwenQAModel

def extract_final_answer(s):
    """提取assistant的最终答案，找不到时返回空串"""
    last_assistant_pos = s.rfind('assistant\n')
    return s[last_assistant_pos+10:].strip() if last_assistant_pos != -1 else ""

def raptor_init() -> RetrievalAugmentation:
    """初始化RAPTOR模型"""
    custom_summarizer = QwenSummarizationModel()
    custom_qa = QwenQAModel()
    custom_embedding = SBertEmbeddingModel()
    custom_config = RetrievalAugmentationConfig(
        summarization_model=custom_summarizer,
        qa_model=custom_qa,
        embedding_model=custom_embedding,
    )
    return RetrievalAugmentation(config=custom_config)

def call_raptor(question: str, context: str) -> str:
    """调用RAPTOR模型获取预测答案"""
    RA = raptor_init()
    RA.add_documents(context)
    raw_answer = RA.answer_question(question=question)
    answer = extract_final_answer(raw_answer)
    del RA
    gc.collect()
    return answer

def normalize_answer(answer: str) -> str:
    """标准化答案格式（转小写、去标点、去空格）"""
    return answer.strip().lower().replace(".", "").replace(" ", "")

def evaluate_dataset(file_path: str) -> None:
    """评估数据集准确率并记录日志（支持中断统计）"""
    correct = 0
    total = 0
    interrupted = False  # 中断状态标记
    
    # 设置日志配置
    base_name = os.path.splitext(file_path)[0]
    iso_str = datetime.datetime.now().isoformat()
    log_filename = f"{base_name}_{iso_str}_log.txt"
    
    logger = logging.getLogger()
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    logging.basicConfig(
        filename=log_filename,
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        filemode='w',
        force=True
    )
    logger.addHandler(logging.StreamHandler())  # 控制台输出

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    try:
                        # 数据处理
                        entry = json.loads(line.strip())
                    except json.JSONDecodeError as e:
                        logging.error(f"Error parsing line: {line[:50]}... | Error: {str(e)}")
                        continue

                    # 问题处理逻辑
                    idx = entry.get("idx", "N/A")
                    question = entry.get("question", "") + "Answer in less than 5-7 words, if no answer, please say 'N/A'."
                    context = entry.get("context", "")
                    targets = entry.get("targets", [])

                    # 模型预测
                    prediction = call_raptor(question, context)
                    normalized_prediction = normalize_answer(prediction)
                    normalized_targets = [normalize_answer("N/A") if t == "" else normalize_answer(t) for t in targets]

                    # 结果统计
                    is_correct = any(target in normalized_prediction for target in normalized_targets)
                    if is_correct:
                        correct += 1
                    total += 1

                    # 日志记录（使用优化后的格式）
                    log_entry = (
                        f"\n===== ENTRY ====="
                        f"\n{'✅' if is_correct else '❌'} [{'CORRECT' if is_correct else 'INCORRECT'}] ID: {idx}"
                        f"\nQuestion: {question}"
                        f"\nPrediction: {prediction} → {'Correct' if is_correct else 'Incorrect'}"
                        f"\nNormalized: {normalized_prediction} vs Targets: {normalized_targets}"
                        f"\n=================\n"
                    )
                    logging.info(log_entry)

                except KeyboardInterrupt:
                    interrupted = True 
                    break

    except KeyboardInterrupt:
        interrupted = True  # 标记中断状态
    finally:
        # 最终统计输出（无论是否中断都会执行）
        accuracy = correct / total if total else 0
        status_prefix = "[INTERRUPTED] Partial results: " if interrupted else "[COMPLETED] Final results: "
        
        final_log = f"{status_prefix}Total={total}, Correct={correct}, Accuracy={accuracy:.2%}"
        logging.info(final_log)
        print("\n" + "="*50)
        print(final_log)
        print("="*50)
        return interrupted

if __name__ == "__main__":
    try:
        # 获取完成状态，正常完成返回0，中断返回1
        interrupted = evaluate_dataset("partial_test_easy.jsonl")
        exit_code = 1 if interrupted else 0
    except Exception as e:  # 其他异常仍然抛出
        print(f"Unexpected error: {str(e)}")
        exit_code = 2
    finally:
        # 确保程序退出 (关键修复点)
        sys.exit(exit_code)

if __name__ == "__main__":
    evaluate_dataset("partial_test_easy.jsonl")