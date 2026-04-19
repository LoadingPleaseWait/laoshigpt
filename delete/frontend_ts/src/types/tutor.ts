export type Correction = {
  original: string;
  corrected: string;
  reason: string;
};

export type VocabularyHighlight = {
  word: string;
  pinyin: string;
  meaning: string;
};

export type TutorTurnResponse = {
  assistant_reply_zh: string;
  pinyin: string;
  english_translation: string;
  corrections: Correction[];
  vocabulary_highlights: VocabularyHighlight[];
  next_question: string;
  session_state: {
    turn_index: number;
    prompt_version: string;
    model: string;
  };
};
