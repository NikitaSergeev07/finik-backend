import json
import httpx
from core.config import get_settings

SYSTEM_PROMPT = """
Ты — преподаватель экономики для детей и подростков. 
Сгенерируй ровно 1 вопрос для викторины по финансовой грамотности и экономике.
Вопрос должен быть интересным, понятным и умеренно сложным.

Верни ответ СТРОГО в формате JSON без кавычек ```json и стороннего текста:
{
  "question": "Текст вопроса?",
  "options": ["Вариант 1", "Вариант 2", "Вариант 3", "Вариант 4"],
  "correct_option_index": 0,
  "reward_coins": 10,
  "explanation": "Краткое и простое объяснение правильного ответа."
}
"""


async def generate_daily_quiz_question() -> dict:
    url = f"{get_settings().deepseek_api_url.rstrip('/')}/chat/completions"
    headers = {
        "Authorization": f"Bearer {get_settings().deepseek_api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": "Сгенерируй новый вопрос по экономике для детей.",
            },
        ],
        "response_format": {"type": "json_object"},
        "temperature": 0.7,
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(url, headers=headers, json=payload)
        response.raise_for_status()

        data = response.json()
        content = data["choices"][0]["message"]["content"]
        return json.loads(content)