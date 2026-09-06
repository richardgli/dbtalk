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