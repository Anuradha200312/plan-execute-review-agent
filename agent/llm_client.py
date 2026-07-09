import os
import json
import httpx
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def call_groq(system_prompt: str, user_prompt: str, json_mode: bool = False) -> str:
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY not set")
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": 0.2
    }
    if json_mode:
        payload["response_format"] = {"type": "json_object"}
        
    response = httpx.post("https://api.groq.com/openai/v1/chat/completions", json=payload, headers=headers, timeout=30.0)
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]

def call_gemini(system_prompt: str, user_prompt: str, json_mode: bool = False) -> str:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY not set")
    
    import google.generativeai as genai
    genai.configure(api_key=api_key)
    
    # Simple generation with system instructions
    model = genai.GenerativeModel(
        model_name="gemini-1.5-flash",
        generation_config={"response_mime_type": "application/json"} if json_mode else None,
        system_instruction=system_prompt
    )
    response = model.generate_content(user_prompt)
    return response.text

def call_openai(system_prompt: str, user_prompt: str, json_mode: bool = False) -> str:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY not set")
    
    from openai import OpenAI
    client = OpenAI(api_key=api_key)
    
    response_format = {"type": "json_object"} if json_mode else None
    
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0.2,
        response_format=response_format
    )
    return response.choices[0].message.content

def call_ollama(system_prompt: str, user_prompt: str, json_mode: bool = False) -> str:
    url = os.environ.get("OLLAMA_API_URL") or os.environ.get("OLLAMA_URL") or "http://localhost:11434/api/chat"
    if "/api/chat" not in url and "/chat/completions" not in url:
        url = url.rstrip("/") + "/api/chat"
        
    model = os.environ.get("OLLAMA_MODEL", "llama3.2")
    timeout = float(os.environ.get("OLLAMA_TIMEOUT", "120.0"))
    api_key = os.environ.get("OLLAMA_API_KEY")
    
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "stream": False,
        "options": {
            "temperature": 0.2
        }
    }
    if json_mode:
        payload["format"] = "json"
        
    response = httpx.post(url, json=payload, headers=headers, timeout=timeout)
    response.raise_for_status()
    return response.json()["message"]["content"]


def call_llm(system_prompt: str, user_prompt: str, json_mode: bool = False) -> str:
    """
    Tries configured LLMs in order of preference:
    1. Groq
    2. Gemini
    3. OpenAI
    4. Ollama (fallback)
    """
    errors = []
    
    # 1. Groq
    if os.environ.get("GROQ_API_KEY"):
        try:
            return call_groq(system_prompt, user_prompt, json_mode)
        except Exception as e:
            errors.append(f"Groq failed: {str(e)}")
            
    # 2. Gemini
    if os.environ.get("GEMINI_API_KEY"):
        try:
            return call_gemini(system_prompt, user_prompt, json_mode)
        except Exception as e:
            errors.append(f"Gemini failed: {str(e)}")
            
    # 3. OpenAI
    if os.environ.get("OPENAI_API_KEY"):
        try:
            return call_openai(system_prompt, user_prompt, json_mode)
        except Exception as e:
            errors.append(f"OpenAI failed: {str(e)}")
            
    # 4. Ollama
    try:
        return call_ollama(system_prompt, user_prompt, json_mode)
    except Exception as e:
        errors.append(f"Ollama failed: {str(e)}")
        
    # Raise composite error if all failed
    raise RuntimeError(f"All LLM providers failed. Errors: {'; '.join(errors)}")
