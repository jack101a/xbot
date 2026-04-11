import os
import io
import base64
import asyncio
from PIL import Image
from google import genai
from google.genai import types
from openai import OpenAI
from dotenv import load_dotenv
import re

load_dotenv()

# --- Key Management ---

class KeyManager:
    def __init__(self, keys_str: str):
        self.keys = [k.strip() for k in keys_str.split(",") if k.strip()]
        self._index = 0
        self._lock = asyncio.Lock()
        
        if not self.keys or "YOUR_KEY" in self.keys[0]:
            print("WARNING: GEMINI_API_KEYS not properly configured in .env")

    async def get_next_key(self) -> str:
        if not self.keys:
            return None
        async with self._lock:
            key = self.keys[self._index % len(self.keys)]
            self._index += 1
            return key

key_manager = KeyManager(os.getenv("GEMINI_API_KEYS", ""))

# --- AI Solvers ---

class GeminiSolver:
    MODEL_NAME = "gemma-4-31b-it"

    async def solve(self, image_b64: str) -> dict:
        for attempt in range(max(1, len(key_manager.keys))):
            api_key = await key_manager.get_next_key()
            if not api_key:
                return {"answer": None, "error": "No Gemini API keys configured."}
            
            try:
                client = genai.Client(api_key=api_key)
                image_bytes = base64.b64decode(image_b64)
                
                response = client.models.generate_content(
                    model=self.MODEL_NAME,
                    contents=[
                        SYSTEM_PROMPT,
                        types.Part.from_bytes(data=image_bytes, mime_type="image/png")
                    ]
                )
                
                text = response.text.strip()
                print(f"DEBUG: Gemini response (Key ending ...{api_key[-4:]}): '{text}'")
                return self.parse_answer(text)
                
            except Exception as e:
                err_msg = str(e).lower()
                if "429" in err_msg or "quota" in err_msg:
                    print(f"WARNING: Key ...{api_key[-4:]} rate limited. Rotating...")
                    continue
                return {"answer": None, "error": f"Gemini error: {str(e)}"}
        
        return {"answer": None, "error": "All Gemini keys exhausted or rate-limited."}

    def parse_answer(self, text: str) -> dict:
        match = re.search(r'\b([1-4])\b', text)
        if match:
            return {"answer": int(match.group(1))}
        return {"answer": None, "error": f"Invalid AI response format: {text}"}


class NvidiaSolver:
    def __init__(self):
        self._update_client()

    def _update_client(self):
        api_key = os.getenv("NVIDIA_API_KEY", "")
        base_url = os.getenv("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1")
        self.model = os.getenv("NVIDIA_MODEL", "nvidia/llama-3.2-90b-vision-instruct")
        
        if api_key and "YOUR_NVIDIA_KEY" not in api_key:
            self.client = OpenAI(base_url=base_url, api_key=api_key)
        else:
            self.client = None

    async def solve(self, image_b64: str) -> dict:
        if not self.client:
            return {"answer": None, "error": "NVIDIA API key not configured."}
        
        try:
            # Wrap synchronous OpenAI call in thread to avoid blocking event loop
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(None, self._call_nvidia, image_b64)
            
            text = response.choices[0].message.content.strip()
            print(f"DEBUG: NVIDIA response: '{text}'")
            return self.parse_answer(text)
            
        except Exception as e:
            return {"answer": None, "error": f"NVIDIA error: {str(e)}"}

    def _call_nvidia(self, image_b64: str):
        return self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": SYSTEM_PROMPT},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/png;base64,{image_b64}"}
                        }
                    ]
                }
            ],
            temperature=0.1,
            max_tokens=10
        )

    def parse_answer(self, text: str) -> dict:
        match = re.search(r'\b([1-4])\b', text)
        if match:
            return {"answer": int(match.group(1))}
        return {"answer": None, "error": f"Invalid AI response format: {text}"}

# --- Module Initialization ---

SYSTEM_PROMPT = """
You are an expert MCQ solver. You will receive an image of a question with 4 answer options labeled 1, 2, 3, or 4.
Return ONLY the number of the correct option: 1, 2, 3, or 4. No explanation.
""".strip()

gemini_solver = GeminiSolver()
nvidia_solver = NvidiaSolver()

async def solve_mcq(image_b64: str, provider: str = "gemini") -> dict:
    if provider == "nvidia":
        return await nvidia_solver.solve(image_b64)
    return await gemini_solver.solve(image_b64)
