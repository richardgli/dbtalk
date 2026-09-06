import SQLBlock from './SQLBlock';
import ResultView from '../components/ResultView';
import type { ChatMessageData } from '../data/types';

interface ChatMessageProps {
  message: ChatMessageData;
}

export default function ChatMessage({ message }: ChatMessageProps) {
  const isUser = message.role === 'user';

  return (
    <div className={`chat-message chat-message--${message.role}`}>
      <div className="chat-message__avatar">{isUser ? 'U' : 'D'}</div>
      <div className="chat-message__body">
        <p className="chat-message__text">{message.text}</p>
        {!isUser && message.sql && <SQLBlock sql={message.sql} />}
        {!isUser && message.rows && <ResultView rows={message.rows} />}
      </div>
    </div>
  );
}