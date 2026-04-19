from pydantic import BaseModel


class ChatTurnRequest(BaseModel):
    session_id: str
    user_id: str
    user_text: str


class Correction(BaseModel):
    original: str
    corrected: str
    reason: str


class VocabularyHighlight(BaseModel):
    word: str
    pinyin: str
    meaning: str


class SessionState(BaseModel):
    turn_index: int
    prompt_version: str
    model: str


class ChatTurnResponse(BaseModel):
    assistant_reply_zh: str
    pinyin: str
    english_translation: str
    corrections: list[Correction]
    vocabulary_highlights: list[VocabularyHighlight]
    next_question: str
    session_state: SessionState
