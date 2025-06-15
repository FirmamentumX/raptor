import json
import gc
import sys
import datetime
import logging
import os
import re
import string
from collections import Counter
from typing import List
from raptor import RetrievalAugmentation, RetrievalAugmentationConfig, SBertEmbeddingModel
from localllm import QwenSummarizationModel, QwenQAModel

os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'

custom_summarizer = QwenSummarizationModel()
custom_qa = QwenQAModel()
custom_embedding = SBertEmbeddingModel()

def normalize_answer(s: str) -> str:
    """Lower text and remove punctuation, articles, and extra whitespace."""
    def remove_articles(text):
        return re.sub(r'\b(a|an|the)\b', ' ', text, flags=re.IGNORECASE)
    def white_space_fix(text):
        return ' '.join(text.split())
    def remove_punc(text):
        exclude = set(string.punctuation)
        return ''.join(ch for ch in text if ch not in exclude)
    def lower(text):
        return text.lower()
    return white_space_fix(remove_articles(remove_punc(lower(s))))

def get_tokens(s: str) -> List[str]:
    return normalize_answer(s).split()

def compute_exact(a_gold: str, a_pred: str) -> int:
    return int(normalize_answer(a_gold) == normalize_answer(a_pred))

def compute_f1(a_gold: str, a_pred: str) -> float:
    gold_toks = get_tokens(a_gold)
    pred_toks = get_tokens(a_pred)
    common = Counter(gold_toks) & Counter(pred_toks)
    num_same = sum(common.values())
    if len(gold_toks) == 0 or len(pred_toks) == 0:
        return int(gold_toks == pred_toks)
    if num_same == 0:
        return 0.0
    precision = num_same / len(pred_toks)
    recall = num_same / len(gold_toks)
    f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) else 0.0
    return f1

def extract_final_answer(s: str) -> str:
    """Extract the final answer from the assistant's response."""
    last_assistant_pos = s.rfind('assistant\n')
    return s[last_assistant_pos+10:].strip() if last_assistant_pos != -1 else ""

def raptor_init() -> RetrievalAugmentation:
    """Initialize RAPTOR model."""
    custom_config = RetrievalAugmentationConfig(
        summarization_model=custom_summarizer,
        qa_model=custom_qa,
        embedding_model=custom_embedding,
    )
    return RetrievalAugmentation(config=custom_config)

def call_raptor(question: str, context: str) -> str:
    """Get predicted answer from RAPTOR model."""
    RA = raptor_init()
    RA.add_documents(context)
    raw_answer = RA.answer_question(question=question)
    answer = extract_final_answer(raw_answer)
    del RA
    gc.collect()
    return answer

def evaluate_dataset(file_path: str) -> None:
    """Evaluate dataset using EM and F1 scores with interruptible logging."""
    em_total = 0.0
    f1_total = 0.0
    total = 0
    interrupted = False

    # Logging setup
    base_name = os.path.splitext(file_path)[0]
    iso_str = datetime.datetime.now().isoformat()
    log_filename = f"{base_name}_{iso_str}_raptor_log.txt"

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
    logger.addHandler(logging.StreamHandler())

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    entry = json.loads(line.strip())
                except json.JSONDecodeError as e:
                    logging.error(f"Error parsing line: {line[:50]}... | Error: {str(e)}")
                    continue

                idx = entry.get("idx", "N/A")
                question = entry.get("question", "") + " Answer in less than 5-7 words, if no answer, say 'N/A'."
                context = entry.get("context", "")
                targets = entry.get("targets", [])

                # Get prediction
                prediction = call_raptor(question, context)
                processed_targets = ["N/A" if t.strip() == "" else t for t in targets]

                # Calculate scores
                em_scores = [compute_exact(t, prediction) for t in processed_targets]
                f1_scores = [compute_f1(t, prediction) for t in processed_targets]
                em_score = max(em_scores) if em_scores else 0.0
                f1_score = max(f1_scores) if f1_scores else 0.0

                em_total += em_score
                f1_total += f1_score
                total += 1

                # Log entry
                log_entry = (
                    f"\n===== ENTRY ====="
                    f"\n{'✅' if em_score == 1 else '❌'} [{'CORRECT' if em_score == 1 else 'INCORRECT'}]ID: {idx}"
                    f"\nQuestion: {question}"
                    f"\nPrediction: {prediction}"
                    f"\nProcessed Targets: {processed_targets}"
                    f"\nEM: {em_score}, F1: {f1_score:.4f}"
                    f"\n=================\n"
                )
                logging.info(log_entry)

    except KeyboardInterrupt:
        interrupted = True
    finally:
        if total > 0:
            em_avg = (em_total / total) * 100
            f1_avg = (f1_total / total) * 100
        else:
            em_avg = f1_avg = 0.0

        status_prefix = "[INTERRUPTED] Partial results: " if interrupted else "[COMPLETED] Final results: "
        final_log = f"{status_prefix}Total={total}, EM={em_avg:.2f}%, F1={f1_avg:.2f}%"
        logging.info(final_log)
        print("\n" + "="*50)
        print(final_log)
        print("="*50)
        return interrupted

if __name__ == "__main__":
    try:
        interrupted = evaluate_dataset("test.easy.jsonl")
        exit_code = 1 if interrupted else 0
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        exit_code = 2
    sys.exit(exit_code)