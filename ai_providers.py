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
    
    uploaded_file = None
    try:
        # Upload file to Gemini
        uploaded_file = gemini_client.files.upload(file=file_path)
        
        def get_state(f):
            return f.state.name if hasattr(f.state, 'name') else f.state

        # Wait for processing
        while get_state(uploaded_file) == "PROCESSING":
            await asyncio.sleep(2)
            uploaded_file = gemini_client.files.get(name=uploaded_file.name)
            
        if get_state(uploaded_file) == "FAILED":
            raise Exception("Gemini AI PDF को प्रोसेस नहीं कर पाया। फाइल करप्ट हो सकती है।")
            
        # Generate content with Auto-Retry for 503 Overload Errors
        prompt = "Extract all the text from this document. Organize it chapter-wise or topic-wise if possible. Do not summarize, give the full text."
        
        max_retries = 3
        response = None
        
        for attempt in range(max_retries):
            try:
                # Run synchronous API call in executor to avoid blocking the bot
                loop = asyncio.get_event_loop()
                def call_generate():
                    return gemini_client.models.generate_content(
                        model=config.GEMINI_MODEL,
                        contents=[uploaded_file, prompt]
                    )
                response = await loop.run_in_executor(None, call_generate)
                break  # Success, exit the retry loop
                
            except Exception as api_error:
                if "503" in str(api_error) and attempt < max_retries - 1:
                    logger.warning(f"Google Server Overloaded (503). Retrying in 5 seconds... (Attempt {attempt+1}/{max_retries})")
                    await asyncio.sleep(5)  # 5 सेकंड रुककर दोबारा ट्राई करें
                else:
                    raise api_error  # अगर 3 बार में भी सर्वर नहीं चला, तो Error दिखा दो
        
        # Delete file from Gemini servers to save space
        if uploaded_file:
            gemini_client.files.delete(name=uploaded_file.name)
        
        return response.text
        
    except Exception as e:
        logger.error(f"PDF Extraction Error: {e}")
        # Cleanup in case of error so we don't waste Gemini storage
        if uploaded_file:
            try:
                gemini_client.files.delete(name=uploaded_file.name)
            except:
                pass
        raise Exception(f"{str(e)}")

async def generate_text_with_fallback(system_prompt: str, user_prompt: str, require_json: bool = False) -> str:
    """Multi-provider fallback logic for text generation"""
    error_logs = []
    
    for provider in config.PROVIDER_ORDER:
        try:
            logger.info(f"Trying provider: {provider}")
            
            if provider == "groq":
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
            
    # अगर सारे फेल हो गए, तो Telegram पर पूरी लिस्ट भेजो
    detailed_errors = "\n".join(error_logs)
    raise Exception(f"सारे AI फेल हो गए। कारण:\n{detailed_errors}")
    
    for provider in config.PROVIDER_ORDER:
        try:
            logger.info(f"Trying provider: {provider}")
            if provider == "groq" and groq_client:
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
                
            elif provider == "cerebras" and cerebras_client:
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
                
            elif provider == "openrouter" and openrouter_client:
                response = await openrouter_client.chat.completions.create(
                    model=config.OPENROUTER_MODEL,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=0.3
                )
                return response.choices[0].message.content
                
            elif provider == "gemini" and gemini_client:
                # Gemini SDK async wrapper
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
            logger.warning(f"Provider {provider} failed: {e}")
            continue # Try next provider
            
    raise Exception("माफ़ करना, अभी सारे AI servers व्यस्त हैं। कृपया कुछ देर बाद प्रयास करें।")
