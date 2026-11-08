import torch
from config import settings
from model_manager import manager

def generate(prompt_messages, temperature=None, top_p=None, max_new_tokens=None):
    if not manager.loaded:
        manager.load()
    temperature = settings.temperature if temperature is None else temperature
    top_p = settings.top_p if top_p is None else top_p
    max_new_tokens = settings.max_new_tokens if max_new_tokens is None else max_new_tokens

    if settings.engine == "llama_cpp":
        prompt = "\n".join(f"{m['role'].upper()}: {m['content']}" for m in prompt_messages) + "\nASSISTANT:"
        result = manager.runtime(prompt, max_tokens=max_new_tokens,
            temperature=max(0.01, temperature), top_p=top_p, repeat_penalty=settings.repetition_penalty,
            stop=["USER:", "SYSTEM:"])
        yield result["choices"][0]["text"]
        return

    tokenizer, model = manager.tokenizer, manager.model
    if hasattr(tokenizer, "apply_chat_template"):
        input_ids = tokenizer.apply_chat_template(
            prompt_messages, tokenize=True, add_generation_prompt=True, return_tensors="pt"
        )
    else:
        prompt = "\n".join(f"{m['role']}: {m['content']}" for m in prompt_messages)
        input_ids = tokenizer(prompt, return_tensors="pt").input_ids
    input_ids = input_ids.to(model.device)
    kwargs = dict(max_new_tokens=max_new_tokens, do_sample=temperature > 0,
                  repetition_penalty=settings.repetition_penalty, pad_token_id=tokenizer.eos_token_id)
    if temperature > 0:
        kwargs.update(temperature=temperature, top_p=top_p)
    with torch.inference_mode():
        output = model.generate(input_ids, **kwargs)
    new_tokens = output[0][input_ids.shape[-1]:]
    # Emit decoded chunks progressively to keep the API contract simple.
    decoded = tokenizer.decode(new_tokens, skip_special_tokens=True)
    words = decoded.split(" ")
    for i, word in enumerate(words):
        yield word if i == 0 else " " + word
