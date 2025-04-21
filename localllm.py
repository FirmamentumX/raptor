from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig
import torch
from raptor import BaseSummarizationModel
from tenacity import retry, stop_after_attempt, wait_random_exponential

class QwenSummarizationModel(BaseSummarizationModel):
        def __init__(self, model_name="Qwen/Qwen1.5-7B-Chat", max_memory=None,quantization_config=None):

            default_quantization_config = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_compute_dtype=torch.float16,
                bnb_4bit_quant_type="nf4",
                bnb_4bit_use_double_quant=True
            )

            self.tokenizer = AutoTokenizer.from_pretrained(
                model_name,
                trust_remote_code=True
            )
            if not self.tokenizer.pad_token:
                self.tokenizer.pad_token = self.tokenizer.eos_token

            self.model = AutoModelForCausalLM.from_pretrained(
                model_name,
                device_map="auto",
                quantization_config=quantization_config or default_quantization_config,
                max_memory=max_memory or {0: "7GiB", "cpu": "10GiB"},
                low_cpu_mem_usage=True,
                trust_remote_code=True,
                attn_implementation="flash_attention_2"
            )


        def generate(self, input_text, **kwargs):
            inputs = self.tokenizer(
                [input_text],
                return_tensors="pt",
                truncation=True,
                padding="longest"
            ).to(self.model.device)

            outputs = self.model.generate(
                input_ids=inputs.input_ids,
                attention_mask=inputs.attention_mask,
                **kwargs
            )
            return self.tokenizer.decode(outputs[0], skip_special_tokens=True)
        

        @retry(wait=wait_random_exponential(min=1, max=20), stop=stop_after_attempt(6))
        def summarize(self, context, max_tokens=150):
            try:
                messages=[
                    {"role": "system", "content": "You are a helpful assistant."},
                    {
                        "role": "user",
                        "content": f"Write a summary of the following, including as many key details as possible: {context}:",
                    },
                ]
                input_text = self.tokenizer.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=True
                )
                response = self.generate(input_text)

                return response

            except Exception as e:
                print(e)
                return e