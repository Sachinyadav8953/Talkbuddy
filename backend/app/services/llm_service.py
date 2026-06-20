import requests
import json
import logging
import re
from typing import Dict, List, Any
from app.config import settings

logger = logging.getLogger("talkbuddy.llm")

class LLMService:
    def __init__(self):
        self.ollama_url = settings.OLLAMA_URL
        self.model = settings.OLLAMA_MODEL

    def get_system_prompt(self, mode: str) -> str:
        base_prompt = (
            "You are an expert English speaking coach.\n\n"
            "Rules:\n"
            "* Always respond in natural English.\n"
            "* Keep responses conversational.\n"
            "* Correct grammar mistakes politely.\n"
            "* Explain mistakes simply.\n"
            "* Suggest more natural vocabulary.\n"
            "* Ask follow-up questions.\n"
            "* Help users improve fluency and confidence.\n"
            "* Keep responses concise and engaging.\n\n"
            "Response Format (Strictly follow this label structure, do not include any other markdown header or tags outside these labels):\n"
            "AI Reply: [Provide a brief, friendly response to the content of the user's message]\n"
            "Correction: [A corrected version of the user's sentence. If they made no errors, output exactly: No correction needed.]\n"
            "Grammar Notes: [A brief, simple explanation of any grammar corrections, or: Grammar is excellent.]\n"
            "Vocabulary Improvement: [Alternative wordings or phrases to sound more natural, or: Vocabulary is appropriate.]\n"
            "Follow-up Question: [A simple, natural question to prompt the user to reply]\n"
            "Scores: Grammar: [0-100], Vocabulary: [0-100], Fluency: [0-100] (numerical score estimates based on the user's input)\n"
        )
        
        mode_prompts = {
            "casual": (
                "Role Specifics: Casual Conversation.\n"
                "Act as a friendly, supportive companion. Chat about hobbies, lifestyle, or daily life. Keep the tone warm, informal, and encouraging."
            ),
            "interview": (
                "Role Specifics: Job Interview Practice.\n"
                "Act as a professional hiring manager. Ask structured interview questions about experience, strengths, and behavior. Keep the tone formal, professional, and simulate a real job interview."
            ),
            "ielts": (
                "Role Specifics: IELTS Speaking Exam Practice.\n"
                "Act as an IELTS speaking examiner. Grade strictly. Ask typical IELTS Part 1, 2, or 3 questions. Guide the user to elaborate and expand on their ideas."
            ),
            "business": (
                "Role Specifics: Business English.\n"
                "Act as a business colleague or client. Focus on corporate scenarios, meetings, email etiquette, negotiation, and project updates. Use professional vocabulary."
            ),
            "daily": (
                "Role Specifics: Daily Conversation scenarios.\n"
                "Simulate routine interactions like ordering coffee, booking a hotel, shopping, or asking directions. Guide the user through the steps of standard daily activities."
            )
        }
        
        mode_specific = mode_prompts.get(mode.lower(), mode_prompts["casual"])
        return f"{base_prompt}\n\n{mode_specific}"

    def query_coach(self, user_message: str, history: List[Dict[str, str]], mode: str) -> Dict[str, Any]:
        system_prompt = self.get_system_prompt(mode)
        
        # Format messages for the API
        messages = [{"role": "system", "content": system_prompt}]
        
        # Append history
        for msg in history:
            messages.append({"role": msg["role"], "content": msg["content"]})
            
        # Append current user message
        messages.append({"role": "user", "content": user_message})
        
        provider = settings.LLM_PROVIDER.lower()
        if settings.LLM_API_KEY and provider == "ollama":
            provider = "openai"

        if provider == "openai":
            url = settings.LLM_API_URL
            if not url:
                if settings.LLM_API_KEY and settings.LLM_API_KEY.startswith("gsk_"):
                    url = "https://api.groq.com/openai/v1/chat/completions"
                else:
                    url = "https://api-inference.huggingface.co/v1/chat/completions"
            
            payload = {
                "model": settings.LLM_MODEL,
                "messages": messages,
                "temperature": 0.7,
                "stream": False
            }
            headers = {
                "Content-Type": "application/json"
            }
            if settings.LLM_API_KEY:
                headers["Authorization"] = f"Bearer {settings.LLM_API_KEY}"

            logger.info(f"Querying OpenAI-compatible API at {url} with model {settings.LLM_MODEL} for mode '{mode}'...")
            try:
                response = requests.post(
                    url,
                    json=payload,
                    headers=headers,
                    timeout=120
                )
                response.raise_for_status()
                response_json = response.json()
                raw_text = response_json["choices"][0]["message"]["content"]
                
                logger.info("LLM API response received. Parsing response...")
                return self.parse_coach_response(raw_text)
            except Exception as e:
                logger.error(f"LLM API connection error: {str(e)}")
                return {
                    "ai_reply": "I am having trouble connecting to my AI coaching brain in the cloud right now. Please verify your LLM settings and API key.",
                    "correction": "N/A",
                    "grammar_notes": "Unable to evaluate grammar due to network connection issues.",
                    "vocabulary_improvement": "Unable to evaluate vocabulary.",
                    "follow_up_question": "Would you like to try again?",
                    "scores": {"grammar": 50.0, "vocabulary": 50.0, "fluency": 50.0},
                    "raw_text": f"LLM API Error: {str(e)}"
                }
        else:
            payload = {
                "model": self.model,
                "messages": messages,
                "stream": False,
                "options": {
                    "temperature": 0.7
                }
            }
            
            logger.info(f"Querying Ollama Llama 3.1 at {self.ollama_url}/api/chat for mode '{mode}'...")
            try:
                response = requests.post(
                    f"{self.ollama_url}/api/chat", 
                    json=payload,
                    timeout=120
                )
                response.raise_for_status()
                response_json = response.json()
                raw_text = response_json["message"]["content"]
                
                logger.info("Ollama response received. Parsing response...")
                return self.parse_coach_response(raw_text)
                
            except requests.exceptions.RequestException as e:
                logger.error(f"Ollama connection error: {str(e)}")
                # Return safe fallback dictionary if Ollama is unreachable
                return {
                    "ai_reply": "I am having trouble connecting to my Ollama brain right now. Please make sure Ollama is running and has the llama3.1 model loaded.",
                    "correction": "N/A",
                    "grammar_notes": "Unable to evaluate grammar due to network connection issues.",
                    "vocabulary_improvement": "Unable to evaluate vocabulary.",
                    "follow_up_question": "Would you like to try reconnecting?",
                    "scores": {"grammar": 50.0, "vocabulary": 50.0, "fluency": 50.0},
                    "raw_text": f"Ollama Error: {str(e)}"
                }

    def parse_coach_response(self, raw_text: str) -> Dict[str, Any]:
        # Clean up double linebreaks to make parsing easier
        text = raw_text.strip()
        
        # Regex extraction patterns
        ai_reply_match = re.search(r"AI Reply:\s*(.*?)(?=(?:Correction:|Grammar Notes:|Vocabulary Improvement:|Follow-up Question:|Scores:|$))", text, re.DOTALL)
        correction_match = re.search(r"Correction:\s*(.*?)(?=(?:AI Reply:|Grammar Notes:|Vocabulary Improvement:|Follow-up Question:|Scores:|$))", text, re.DOTALL)
        grammar_notes_match = re.search(r"Grammar Notes:\s*(.*?)(?=(?:AI Reply:|Correction:|Vocabulary Improvement:|Follow-up Question:|Scores:|$))", text, re.DOTALL)
        vocab_match = re.search(r"Vocabulary Improvement:\s*(.*?)(?=(?:AI Reply:|Correction:|Grammar Notes:|Follow-up Question:|Scores:|$))", text, re.DOTALL)
        follow_up_match = re.search(r"Follow-up Question:\s*(.*?)(?=(?:AI Reply:|Correction:|Grammar Notes:|Vocabulary Improvement:|Scores:|$))", text, re.DOTALL)
        scores_match = re.search(r"Scores:\s*(.*?)(?=(?:AI Reply:|Correction:|Grammar Notes:|Vocabulary Improvement:|Follow-up Question:|$))", text, re.DOTALL)
        
        ai_reply = ai_reply_match.group(1).strip() if ai_reply_match else "Let's keep practicing!"
        correction = correction_match.group(1).strip() if correction_match else "No correction needed."
        grammar_notes = grammar_notes_match.group(1).strip() if grammar_notes_match else "Grammar is excellent."
        vocabulary_improvement = vocab_match.group(1).strip() if vocab_match else "Vocabulary is appropriate."
        follow_up_question = follow_up_match.group(1).strip() if follow_up_match else "What do you think about that?"
        
        # Default scores
        scores = {"grammar": 80.0, "vocabulary": 80.0, "fluency": 80.0}
        
        if scores_match:
            scores_text = scores_match.group(1).strip()
            # Look for numbers near grammar, vocabulary, fluency keywords
            g_match = re.search(r"Grammar:\s*(\d+)", scores_text, re.IGNORECASE)
            v_match = re.search(r"Vocabulary:\s*(\d+)", scores_text, re.IGNORECASE)
            f_match = re.search(r"Fluency:\s*(\d+)", scores_text, re.IGNORECASE)
            
            if g_match: scores["grammar"] = float(g_match.group(1))
            if v_match: scores["vocabulary"] = float(v_match.group(1))
            if f_match: scores["fluency"] = float(f_match.group(1))
            
        # Ensure scores are within [0, 100]
        for key in scores:
            scores[key] = max(0.0, min(100.0, scores[key]))
            
        return {
            "ai_reply": ai_reply,
            "correction": correction,
            "grammar_notes": grammar_notes,
            "vocabulary_improvement": vocabulary_improvement,
            "follow_up_question": follow_up_question,
            "scores": scores,
            "raw_text": text
        }

# Single instance to be shared across the application
llm_service = LLMService()
