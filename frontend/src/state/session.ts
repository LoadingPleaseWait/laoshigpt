export type SessionMode = 'free_chat' | 'scenario';

export type LocalSessionState = {
  sessionId?: string;
  mode?: SessionMode;
  scenario?: 'food_ordering' | 'self_intro' | 'directions';
  turnCount: number;
};

export const initialSessionState: LocalSessionState = {
  turnCount: 0,
};
