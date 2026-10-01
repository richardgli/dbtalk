export type Role = 'user' | 'assistant';

export interface QueryResultRow {
  [column: string]: string | number | boolean | null;
}

export interface ChatMessageData {
  role: Role;
  text: string;
  sql?: string;
  rows?: QueryResultRow[];
}

export interface QueryRequest {
  question: string;
  session_id: string;
}

export interface QueryResponse {
  answer: string;
  sql: string;
  results: QueryResultRow[];
}

export interface Conversation {
  id: string;
  created_at: string;
  updated_at: string;
  title: string | null;
}

export interface MessageResponse {
  role: Role;
  text: string;
  sql: string | null;
  rows: QueryResultRow[] | null;
}