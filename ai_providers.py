import asyncio
import json
from google import genai
from google.genai import types
from groq import AsyncGroq
from openai import AsyncOpenAI
import config
from config import logger

# Initialize Clients
try:
    gemini_client = genai.Client(api_key=config.GEMINI_API_KEY)
except Exception as e:
    logger.error(f"Gemini init failed: {e}")
    gemini_client = None

# APMix Client (OpenAI फॉर्मेट पर काम करता है)
try:
    apmix_client = AsyncOpenAI(api_key=config.APMIX_API_KEY, base_url="https://api.apmix.ai/v1")
except:
    apmix_client = None

try:
    groq_client = AsyncGroq(api_key=config.GROQ_API_KEY)
except:
    groq_client = None

try:
    cerebras_client = AsyncOpenAI(api_key=config.CEREBRAS_API_KEY, base_url="https://api.cerebras.ai/v1")
except:
    cerebras_client = None

try:
    openrouter_client = AsyncOpenAI(api_key=config.OPENROUTER_API_KEY, base_url="https://openrouter.ai/api/v1")
except:
    openrouter_client = None


async def extract_text_from_pdf(file_path: str, mime_type: str = "application/pdf") -> str:
    """सिर्फ Gemini का इस्तेमाल करके PDF से text निकालना (One-time process)"""
    if not gemini_client:
        raise Exception("Gemini API Key configure नहीं की गई है। कृपया अपनी Keys चेक करें।")
    
    max_retries = 3
    last_error = ""
    
    for attempt in range(max_retries):
        uploaded_file = None
        try:
            loop = asyncio.get_event_loop()
            
            uploaded_file = await loop.run_in_executor(
                None, lambda: gemini_client.files.upload(file=file_path)
            )
            
            def get_state(f):
                return f.state.name if hasattr(f.state, 'name') else f.state

            while get_state(uploaded_file) == "PROCESSING":
                await asyncio.sleep(2)
                uploaded_file = await loop.run_in_executor(
                    None, lambda: gemini_client.files.get(name=uploaded_file.name)
                )
                
            if get_state(uploaded_file) == "FAILED":
                raise Exception("Gemini AI PDF को प्रोसेस नहीं कर पाया।")
                
            prompt = "Extract all the text from this document. Organize it chapter-wise or topic-wise if possible. Do not summarize, give the full text."
            
            def call_generate():
                return gemini_client.models.generate_content(
                    model=config.GEMINI_MODEL,
                    contents=[uploaded_file, prompt]
                )
            response = await loop.run_in_executor(None, call_generate)
            
            await loop.run_in_executor(None, lambda: gemini_client.files.delete(name=uploaded_file.name))
            return response.text
            
        except Exception as e:
            last_error = str(e)
            logger.warning(f"Gemini Attempt {attempt+1} failed: {last_error}")
            
            if uploaded_file:
                try:
                    await loop.run_in_executor(None, lambda: gemini_client.files.delete(name=uploaded_file.name))
                except:
                    pass
                    
            if attempt < max_retries - 1:
                await asyncio.sleep(5) 
            else:
                raise Exception(f"Google Server Error: {last_error}")

async def generate_text_with_fallback(system_prompt: str, user_prompt: str, require_json: bool = False) -> str:
    """Multi-provider fallback logic for text generation"""
    error_logs = []
    
    for provider in config.PROVIDER_ORDER:
        try:
            logger.info(f"Trying provider: {provider}")
            
            # --- नया APMIX सपोर्ट ---
            if provider == "apmix":
                if not apmix_client or config.APMIX_API_KEY == "apx_live_p0zl5zA2PqjOSKZTBZrOEwKnxwDkpCk6g6CvYV8R":
                    error_logs.append("APMix: API Key missing or default")
                    continue
                response = await apmix_client.chat.completions.create(
                    model=config.APMIX_MODEL,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    response_format={"type": "json_object"} if require_json else None,
                    temperature=0.3
                )
                return response.choices[0].message.content
                
            elif provider == "groq":
                if not groq_client:
                    error_logs.append("Groq: API Key missing")
                    continue
                response = await groq_client.chat.completions.create(
                    model=config.GROQ_MODEL,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    response_format={"type": "json_object"} if require_json else None,
                    temperature=0.3
                )
                return response.choices[0].message.content
                
            elif provider == "cerebras":
                if not cerebras_client:
                    error_logs.append("Cerebras: API Key missing")
                    continue
                response = await cerebras_client.chat.completions.create(
                    model=config.CEREBRAS_MODEL,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    response_format={"type": "json_object"} if require_json else None,
                    temperature=0.3
                )
                return response.choices[0].message.content
                
            elif provider == "openrouter":
                if not openrouter_client:
                    error_logs.append("OpenRouter: API Key missing")
                    continue
                response = await openrouter_client.chat.completions.create(
                    model=config.OPENROUTER_MODEL,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=0.3
                )
                return response.choices[0].message.content
                
            elif provider == "gemini":
                if not gemini_client:
                    error_logs.append("Gemini: API Key missing")
                    continue
                loop = asyncio.get_event_loop()
                def call_gemini():
                    return gemini_client.models.generate_content(
                        model=config.GEMINI_MODEL,
                        contents=[f"System: {system_prompt}\n\nUser: {user_prompt}"],
                        config=types.GenerateContentConfig(
                            response_mime_type="application/json" if require_json else "text/plain",
                            temperature=0.3
                        )
                    )
                response = await loop.run_in_executor(None, call_gemini)
                return response.text
                
        except Exception as e:
            error_logs.append(f"{provider}: {str(e)}")
            continue 
            
    detailed_errors = "\n".join(error_logs)
    raise Exception(f"सारे AI फेल हो गए। कारण:\n{detailed_errors}")
