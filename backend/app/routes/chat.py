from fastapi import APIRouter

from app.schemas.chat import ChatTurnRequest, ChatTurnResponse, Correction, SessionState, VocabularyHighlight

router = APIRouter()


@router.post("/turn", response_model=ChatTurnResponse)
def chat_turn(payload: ChatTurnRequest) -> ChatTurnResponse:
    return ChatTurnResponse(
        assistant_reply_zh="很好，我们继续练习。",
        pinyin="Hěn hǎo, wǒmen jìxù liànxí.",
        english_translation="Great, let's continue practicing.",
        corrections=[
            Correction(
                original=payload.user_text,
                corrected=payload.user_text,
                reason="No correction for scaffold response.",
            )
        ],
        vocabulary_highlights=[
            VocabularyHighlight(word="继续", pinyin="jìxù", meaning="continue")
        ],
        next_question="你今天想练习什么话题？",
        session_state=SessionState(turn_index=1, prompt_version="scaffold-v0", model="mock"),
    )
