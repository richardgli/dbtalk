import { useState, useRef, useEffect, type SubmitEvent } from 'react';
import ChatMessage from '../components/ChatMessage';
import type { ChatMessageData, QueryRequest, QueryResponse } from '../data/types';

const API_URL: string = import.meta.env.VITE_API_URL;

export default function ChatPanel() {
  const [messages, setMessages] = useState<ChatMessageData[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [sessionId] = useState<string>(() => crypto.randomUUID());
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  async function sendQuestion(question: string) {
    if (!question.trim() || loading) return;

    setMessages((prev) => [...prev, { role: 'user', text: question }]);
    setInput('');
    setLoading(true);

    try {
      const body: QueryRequest = { question, session_id: sessionId };
      const res = await fetch(`${API_URL}/api/query`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });

      if (!res.ok) throw new Error(`Request failed: ${res.status}`);

      const data: QueryResponse = await res.json();
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', text: data.answer, sql: data.sql, rows: data.results },
      ]);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Unknown error';
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', text: `Something went wrong: ${message}` },
      ]);
    } finally {
      setLoading(false);
    }
  }

  const handleSubmit = (e: SubmitEvent<HTMLFormElement>) => {
    e.preventDefault();
    sendQuestion(input);
  }

  return (
    <div className="chat-panel">
      <div className="chat-panel__main">
        <header className="chat-panel__header">
          <div className="chat-panel__brand">
            <img className="chat-panel__brand-mark" src="/dbtalk_logo.png" alt="dbtalk logo" />
            <div>
              <h1>dbtalk</h1>
              <p>Ask your data anything</p>
            </div>
          </div>
        </header>
        <div className="chat-panel__messages">
          {messages.length === 0 && (
            <p className="chat-panel__placeholder">
              Ask a question about the database, e.g. "what was Paris' average
              temperature in August 2026?"
            </p>
          )}
          {messages.map((m, i) => <ChatMessage key={i} message={m} />)}
          {loading && <p className="chat-panel__thinking">thinking…</p>}
          <div ref={bottomRef} />
        </div>

        <form className="chat-panel__input-row" onSubmit={handleSubmit}>
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask about your data..."
            disabled={loading}
          />
          <button type="submit" disabled={loading || !input.trim()}>
            Send
          </button>
        </form>
      </div>
    </div>
  );
}