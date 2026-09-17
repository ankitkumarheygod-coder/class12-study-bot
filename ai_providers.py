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
        raise Exception("Gemini client is not configured.")
    
    try:
        # Upload file to Gemini
        uploaded_file = gemini_client.files.upload(file=file_path, config={'mime_type': mime_type})
        
        # Wait for processing
        while uploaded_file.state.name == "PROCESSING":
            await asyncio.sleep(2)
            uploaded_file = gemini_client.files.get(name=uploaded_file.name)
            
        if uploaded_file.state.name == "FAILED":
            raise Exception("Gemini failed to process the document.")
            
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
        raise Exception("PDF पढ़ने में कोई तकनीकी समस्या आ गई। कृपया दोबारा कोशिश करें।")

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
                # Gemini SDK async wrapper (running sync in executor to avoid blocking)
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
