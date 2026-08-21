import os
import re
import json
import asyncio
import threading
from abc import ABC, abstractmethod
from typing import AsyncIterator, Dict, Any, Optional, List
from schemas import CrisisSituationReport

# HuggingFace & PyTorch Lazy Loader
_hf_model = None
_hf_tokenizer = None
_hf_lock = threading.Lock()


def get_hf_pipeline():
    """Singleton lazy loader for local Hugging Face in-memory model."""
    global _hf_model, _hf_tokenizer
    with _hf_lock:
        if _hf_model is None or _hf_tokenizer is None:
            import torch
            from transformers import AutoModelForCausalLM, AutoTokenizer
            
            model_name = os.environ.get("LOCAL_HF_MODEL", "Qwen/Qwen2.5-0.5B-Instruct")
            print(f"[Local LLM] Initializing in-memory Hugging Face model: {model_name}...")
            
            _hf_tokenizer = AutoTokenizer.from_pretrained(model_name)
            # Use float32 on CPU or float16 if CUDA is available
            dtype = torch.float16 if torch.cuda.is_available() else torch.float32
            _hf_model = AutoModelForCausalLM.from_pretrained(model_name, dtype=dtype)
            if torch.cuda.is_available():
                _hf_model = _hf_model.to("cuda")
            _hf_model.eval()
            print(f"[Local LLM] Model {model_name} successfully loaded into memory!")
            
    return _hf_model, _hf_tokenizer


class BaseLLMProvider(ABC):
    """Abstract Base Class defining the unified interface for all LLM providers."""
    
    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    async def is_available(self) -> bool:
        pass

    @abstractmethod
    async def generate_response(self, prompt: str, system_prompt: str = "") -> str:
        pass

    @abstractmethod
    async def stream_response(self, prompt: str, system_prompt: str = "") -> AsyncIterator[str]:
        pass


class HuggingFaceLocalLLMProvider(BaseLLMProvider):
    """In-Memory Local Hugging Face LLM (Qwen2.5 / TinyLlama) running 100% locally with zero APIs."""

    @property
    def name(self) -> str:
        model_name = os.environ.get("LOCAL_HF_MODEL", "Qwen/Qwen2.5-0.5B-Instruct")
        return f"Local In-Memory LLM ({model_name.split('/')[-1]})"

    async def is_available(self) -> bool:
        try:
            get_hf_pipeline()
            return True
        except Exception as e:
            print(f"[Local LLM] Availability check notice: {e}")
            return False

    async def generate_response(self, prompt: str, system_prompt: str = "") -> str:
        model, tokenizer = get_hf_pipeline()
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        inputs = tokenizer([text], return_tensors="pt")
        if hasattr(model, "device"):
            inputs = {k: v.to(model.device) for k, v in inputs.items()}

        loop = asyncio.get_event_loop()
        
        def _run_inference():
            with __import__("torch").no_grad():
                outputs = model.generate(
                    **inputs,
                    max_new_tokens=350,
                    do_sample=True,
                    temperature=0.4,
                    top_p=0.9,
                    repetition_penalty=1.1,
                    pad_token_id=tokenizer.eos_token_id
                )
            gen_tokens = outputs[0][len(inputs["input_ids"][0]):]
            return tokenizer.decode(gen_tokens, skip_special_tokens=True).strip()

        result = await loop.run_in_executor(None, _run_inference)
        # Format bold and line breaks for web presentation
        result = re.sub(r"\*\*(.*?)\*\*", r"<strong>\1</strong>", result)
        result = result.replace("\n", "<br>")
        return result

    async def stream_response(self, prompt: str, system_prompt: str = "") -> AsyncIterator[str]:
        model, tokenizer = get_hf_pipeline()
        from transformers import TextIteratorStreamer

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        inputs = tokenizer([text], return_tensors="pt")
        if hasattr(model, "device"):
            inputs = {k: v.to(model.device) for k, v in inputs.items()}

        streamer = TextIteratorStreamer(tokenizer, skip_prompt=True, skip_special_tokens=True)
        generation_kwargs = dict(
            **inputs,
            streamer=streamer,
            max_new_tokens=350,
            do_sample=True,
            temperature=0.4,
            top_p=0.9,
            repetition_penalty=1.1,
            pad_token_id=tokenizer.eos_token_id
        )

        thread = threading.Thread(target=model.generate, kwargs=generation_kwargs)
        thread.start()

        for chunk in streamer:
            if chunk:
                yield chunk
                await asyncio.sleep(0.01)

        thread.join()


class LocalHeuristicProvider(BaseLLMProvider):
    """Zero-network, deterministic rule-based NLP intelligence engine."""

    @property
    def name(self) -> str:
        return "CrisisAid Local Intelligence Engine"

    async def is_available(self) -> bool:
        return True

    async def generate_response(self, prompt: str, system_prompt: str = "") -> str:
        p_lower = prompt.lower()
        
        if any(w in p_lower for w in ["safety", "preparedness", "tips", "survival", "first aid"]):
            return (
                "🛡️ <strong>Emergency Disaster Preparedness Guidelines:</strong><br><br>"
                "• <strong>Emergency Kit:</strong> Maintain a 72-hour supply of water (1 gallon/person/day), non-perishable food, flashlights, and a battery-powered radio.<br>"
                "• <strong>Medical Readiness:</strong> Keep essential prescription medications, a trauma first-aid kit, and water purification tablets ready.<br>"
                "• <strong>Evacuation Plan:</strong> Establish emergency contact channels and know your local civil defense evacuation routes.<br>"
                "• <strong>Communication:</strong> In severe crises, SMS often succeeds when cellular voice channels are congested."
            )

        if any(w in p_lower for w in ["donate", "donation", "funds", "give", "help", "support"]):
            return (
                "💸 <strong>Verified Humanitarian Relief Channels:</strong><br><br>"
                "• <strong>Emergency Trauma & Healthcare:</strong> <a href='https://www.msf.org/donate' target='_blank'>Doctors Without Borders (MSF)</a><br>"
                "• <strong>Food Security & Nutrition:</strong> <a href='https://www.wfp.org/donate' target='_blank'>UN World Food Programme (WFP)</a><br>"
                "• <strong>Refugee Shelter & Legal Protection:</strong> <a href='https://donate.unhcr.org/' target='_blank'>UN Refugee Agency (UNHCR)</a><br>"
                "• <strong>Neutral Rapid Relief Corridors:</strong> <a href='https://www.icrc.org/en/donate' target='_blank'>International Committee of the Red Cross (ICRC)</a><br><br>"
                "<em>All listed funds operate with verified international accreditation.</em>"
            )

        return (
            "🚨 <strong>Humanitarian Crisis Intelligence Summary:</strong><br><br>"
            "Active frontline operations and emergency monitoring continue across key crisis belts.<br><br>"
            "Immediate priorities include emergency trauma care, clean water purification, and civilian protection corridors. "
            "You can explore real-time coordinates on our <strong><a href='/locate'>Global Crisis Radar Map</a></strong>."
        )

    async def stream_response(self, prompt: str, system_prompt: str = "") -> AsyncIterator[str]:
        full_text = await self.generate_response(prompt, system_prompt)
        words = re.split(r'(\s+)', full_text)
        for w in words:
            if w:
                yield w
                await asyncio.sleep(0.015)


class LLMServiceFactory:
    """Factory and orchestrator prioritizing your in-memory local LLM with 0 external APIs."""

    _providers = {
        "local_hf": HuggingFaceLocalLLMProvider(),
        "local_rule": LocalHeuristicProvider()
    }

    @classmethod
    def get_provider(cls, preferred_name: Optional[str] = None) -> BaseLLMProvider:
        if preferred_name and preferred_name.lower() in cls._providers:
            return cls._providers[preferred_name.lower()]
        return cls._providers["local_hf"]

    @classmethod
    async def generate_with_fallback(cls, prompt: str, system_prompt: str = "", preferred: Optional[str] = None) -> tuple[str, str]:
        """Runs your local in-memory LLM with zero external cloud APIs."""
        order = []
        if preferred and preferred.lower() in cls._providers:
            order.append(cls._providers[preferred.lower()])
        
        # Priority: Local In-Memory HuggingFace Model -> Local Rule Engine
        for p in [cls._providers["local_hf"], cls._providers["local_rule"]]:
            if p not in order:
                order.append(p)

        for provider in order:
            try:
                if await provider.is_available():
                    result = await provider.generate_response(prompt, system_prompt)
                    if result and len(result) > 5:
                        return result, provider.name
            except Exception as e:
                print(f"[Local LLM Engine] Provider {provider.name} notice: {e}. Cascading...")

        # Ultimate fallback
        result = await cls._providers["local_rule"].generate_response(prompt, system_prompt)
        return result, cls._providers["local_rule"].name

    @classmethod
    async def stream_with_fallback(cls, prompt: str, system_prompt: str = "", preferred: Optional[str] = None) -> AsyncIterator[Dict[str, Any]]:
        """Streams real-time tokens from your local LLM directly to the browser."""
        provider = cls.get_provider(preferred)
        try:
            if await provider.is_available():
                yield {"type": "meta", "provider": provider.name}
                async for chunk in provider.stream_response(prompt, system_prompt):
                    # Format bold markers and linebreaks cleanly
                    formatted_chunk = chunk.replace("\n", "<br>")
                    yield {"type": "token", "chunk": formatted_chunk}
                yield {"type": "done"}
                return
        except Exception as e:
            print(f"[Local LLM Engine] Streaming fallback notice: {e}")

        # Fallback to local rule engine
        fb_provider = cls._providers["local_rule"]
        yield {"type": "meta", "provider": fb_provider.name}
        async for chunk in fb_provider.stream_response(prompt, system_prompt):
            yield {"type": "token", "chunk": chunk}
        yield {"type": "done"}
