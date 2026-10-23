"""Pembungkus tipis untuk API yang kompatibel dengan OpenAI."""
import json
import logging
import os
import re
import time

from openai import OpenAI

log = logging.getLogger(__name__)


def parse_json(text):
    """Ambil JSON dari balasan LLM (toleran terhadap ```json ... ``` dan teks tambahan)."""
    text = (text or "").strip()
    text = re.sub(r"^```(?:json)?|```$", "", text, flags=re.MULTILINE).strip()
    starts = [i for i in (text.find("["), text.find("{")) if i != -1]
    if not starts:
        raise ValueError("Tidak ada JSON pada balasan")
    start = min(starts)
    end = max(text.rfind("]"), text.rfind("}"))
    return json.loads(text[start : end + 1])


class LLM:
    def __init__(self, cfg):
        lcfg = cfg["llm"]
        key = os.getenv(lcfg["api_key_env"])
        if not key:
            raise RuntimeError(
                f"API key belum diisi. Isi {lcfg['api_key_env']} di file .env"
            )
        self.client = OpenAI(api_key=key, base_url=lcfg["base_url"])
        self.model = lcfg["model"]
        self.embedding_model = lcfg.get("embedding_model")

    def chat_json(self, system, user, retries=2):
        """Panggil LLM dan kembalikan hasil JSON; None jika semua percobaan gagal."""
        for attempt in range(retries + 1):
            try:
                resp = self.client.chat.completions.create(
                    model=self.model,
                    temperature=0.2,
                    messages=[
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                )
                return parse_json(resp.choices[0].message.content)
            except Exception as e:  # noqa: BLE001
                log.warning("Panggilan LLM gagal (percobaan %d): %s", attempt + 1, e)
                time.sleep(2 * (attempt + 1))
        return None

    def embed(self, texts, batch=100):
        vectors = []
        for i in range(0, len(texts), batch):
            resp = self.client.embeddings.create(
                model=self.embedding_model, input=texts[i : i + batch]
            )
            vectors.extend(d.embedding for d in resp.data)
        return vectors
