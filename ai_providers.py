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
    
    try:
        # Upload file to Gemini (SDK will auto-detect PDF format)
        uploaded_file = gemini_client.files.upload(file=file_path)
        
        # Helper function to handle both Enum and String states across different SDK versions
        def get_state(f):
            return f.state.name if hasattr(f.state, 'name') else f.state

        # Wait for processing
        while get_state(uploaded_file) == "PROCESSING":
            await asyncio.sleep(2)
            uploaded_file = gemini_client.files.get(name=uploaded_file.name)
            
        if get_state(uploaded_file) == "FAILED":
            raise Exception("Gemini AI PDF को प्रोसेस नहीं कर पाया। फाइल करप्ट हो सकती है।")
            
        # Generate content (Extract text)
        prompt = "Extract all the text from this document. Organize it chapter-wise or topic-wise if possible. Do not summarize, give the full text."
        response = gemini_client.models.generate_content(
            model=config.GEMINI_MODEL,
            contents=[uploaded_file, prompt]
        )
        
        # Delete file from Gemini servers to save space
        gemini_client.files.delete(name=uploaded_file.name)
        
        return response.text
    except Exception as e:
        logger.error(f"PDF Extraction Error: {e}")
        # अब यह असली Error Message Telegram पर भेजेगा ताकि आपको पता चले दिक्कत कहाँ है
        raise Exception(f"{str(e)}")

async def generate_text_with_fallback(system_prompt: str, user_prompt: str, require_json: bool = False) -> str:
    """Multi-provider fallback logic for text generation"""
    
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
