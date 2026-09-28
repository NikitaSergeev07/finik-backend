"""Фильтр входа и выхода ИИ. Без модели: стоп-лист, карты, ссылки, обрезка текста."""

import re

from domain import rules

# Стебли, не отдельные слова: ловят формы. Короткие вроде «сук» не берём — много ложных.
_STEMS = (
    "бляд",
    "хуй",
    "хуя",
    "хуе",
    "пизд",
    "ебан",
    "ебат",
    "ёбан",
    "сука",
    "мудак",
    "секс",
    "порно",
    "интим",
    "нарко",
    "кокаин",
    "героин",
    "сигарет",
    "суицид",
    "самоубий",
    "cvv",
    "cvc",
    "парол",
    "номер карты",
)

_URL = re.compile(r"(https?://|t\.me/|www\.)", re.IGNORECASE)
_CARD = re.compile(r"(?<!\d)\d(?:[\s-]?\d){12,18}(?!\d)")
_SPACES = re.compile(r"\s+")
_MARKDOWN = re.compile(r"[*_`#>]{1,3}")
_SENTENCES = re.compile(r"(?<=[.!?…])\s+")


def normalize(text: str) -> str:
    lowered = text.lower().replace("ё", "е")
    cleaned = re.sub(r"[^a-zа-я0-9\s]", " ", lowered)
    return _SPACES.sub(" ", cleaned).strip()


def is_blocked(text: str) -> bool:
    if not text or not text.strip():
        return False
    if _URL.search(text) or _CARD.search(text):
        return True
    compact = re.sub(r"[\s-]", "", text)
    if re.search(r"\d{13,19}", compact):
        return True
    blob = normalize(text)
    return any(stem in blob for stem in _STEMS)


def sanitize(text: str, *, limit: int = rules.AI_REMARK_CHARS, sentences: int | None = None) -> str:
    """Выход модели: без кавычек и разметки, коротко, одной мыслью."""
    cut = _MARKDOWN.sub("", text).strip().strip("\"'«»")
    cut = _SPACES.sub(" ", cut).strip()
    if sentences:
        parts = _SENTENCES.split(cut)
        cut = " ".join(parts[:sentences]).strip()
    if len(cut) > limit:
        cut = cut[:limit].rsplit(" ", 1)[0].rstrip(".,;:") + "."
    return cut
