import logging
import httpx
from core.config import Settings
from dataclasses import dataclass

log = logging.getLogger(__name__)

class DeepSeekError(RuntimeError):
    """Ошибка при обращении к DeepSeek API."""

@dataclass(slots=True)
class DeepSeekClient:
    settings: Settings
    _http: httpx.AsyncClient | None = None

    def _client(self) -> httpx.AsyncClient:
        if self._http is None:
            self._http = httpx.AsyncClient(
                base_url=self.settings.deepseek_api_url,
                headers={
                    "Authorization": f"Bearer {self.settings.deepseek_api_key}",
                    "Content-Type": "application/json",
                },
                timeout=20.0,
                verify=False
            )
        return self._http
    
    async def aclose(self) -> None:
        if self._http is not None:
            await self._http.aclose()
            self._http = None
    
    async def generate_pet_diary(
        self,
        pet_name: str,
        species_name: str,
        day_number: int,
        events: list[str] | str,
    ) -> str:
        """Генерирует короткую запись в дневник питомца на основе логов дня."""
        if isinstance(events, list):
            events_text = "\n".join(f"- {e}" for e in events if e.strip())
        else:
            events_text = events.strip()

        if not events_text:
            events_text = "Сегодня день прошёл тихо и без особых событий."

        prompt = (
            f"Ты — {pet_name}, милый мистический росток ({species_name}) из детской игры про финансовую грамотность.\n"
            f"Сегодня завершился День {day_number} игровой недели.\n\n"
            f"Вот список событий, которые произошли за сегодня:\n"
            f"{events_text}\n\n"
            f"Напиши короткую, уютную и милую запись в свой личный дневничок (2–4 предложения) от первого лица ('Я сегодня...').\n"
            f"Расскажи о своих впечатлениях за день простым детским языком, порадуйся заботе или упомяни покупки/планы. "
            f"Не используй сложные термины и нотации."
        )

        try:
            response = await self._client().post(
                "/chat/completions",
                json={
                    "model": self.settings.deepseek_model,
                    "messages": [
                        {
                            "role": "system",
                            "content": "Ты персонаж детской игры. Пишешь милые и короткие записи в дневник от первого лица.",
                        },
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": 0.8,
                    "max_tokens": 250,
                },
            )
            response.raise_for_status()
            data = response.json()
            return str(data["choices"][0]["message"]["content"]).strip()
        except Exception as exc:
            log.error(f"DeepSeek diary generation failed: {exc}")
            # Резервный ответ на случай ошибки API
            return (
                f"День {day_number} заново записан в мой дневничок! "
                f"Спасибо за заботу, мне очень нравится расти вместе с тобой!"
            )


    async def generate_dream_plan(self, dream: str, rules: str) -> str:
        try:
            response = await self._client().post(
                "/chat/completions",
                json={
                    "model": self.settings.deepseek_model,
                    "messages": [
                        {
                            "role": "system", 
                            "content": "Ты — дружелюбный финансовый помощник для детей в игре «Финик».\n"
                                    "Твоя задача — составить простой, понятный и мотивирующий пошаговый план действий "
                                    "для достижения мечты ребёнка с учётом правил игры."
                        },
                        {
                            "role": "user", 
                            "content": f"Мечта: {dream}\n"
                                    f"Правила игры и условия: {rules}\n\n"
                                    "Напиши короткий и понятный план действий (3-5 шагов), на «ты», без сложных терминов."
                        },
                    ],
                    "temperature": 0.7,
                },
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]
        except Exception as exc:
            log.error(f"DeepSeek generation failed: {exc}")
            return "Не удалось сформировать план. Попробуй позже!"
        

    async def generate_word_of_day(self) -> tuple[str, str]:
        """Возвращает кортеж: (Слово, Объяснение для ребенка)."""
        prompt = (
            "Выбери рандомное, но интересное понятие из мира финансов или экономики для детей 8-12 лет "
            "Дай ответ STRICTLY в формате JSON с двумя полями:\n"
            '{"word": "Слово", "explanation": "Простое и понятное объяснение в 4-6 предложениях с понятным ребенку примером"}'
        )
        
        try:
            response = await self._client().post(
                "/chat/completions",
                json={
                    "model": self.settings.deepseek_model,
                    "messages": [
                        {"role": "system", "content": "Ты финансовый помощник для детей. Отвечай только валидным JSON."},
                        {"role": "user", "content": prompt},
                    ],
                    "response_format": {"type": "json_object"},
                    "temperature": 0.7,
                },
            )
            response.raise_for_status()
            data = response.json()
            
            import json
            content = json.loads(data["choices"][0]["message"]["content"])
            return content["word"], content["explanation"]
            
        except Exception as exc:
            log.error(f"DeepSeek generation failed: {exc}")
            # Резервный фолбэк на случай сбоя API, чтобы API не падал
            return "Сбережения", "Это деньги, которые ты не потратил сразу, а отложил на будущее, чтобы купить что-то важное."