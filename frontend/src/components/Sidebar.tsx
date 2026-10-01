import type { Conversation } from '../data/types';

interface SidebarProps {
  conversations: Conversation[];
  activeId: string;
  onSelect: (id: string) => void;
  onNewChat: () => void;
}

function conversationLabel(conv: Conversation): string {
  if (conv.title && conv.title.trim()) return conv.title;
  return 'New conversation';
}

export default function Sidebar({ conversations, activeId, onSelect, onNewChat }: SidebarProps) {
  return (
    <aside className="sidebar">
      <div className="sidebar__header">
        <span className="sidebar__title">Chats</span>
        <button className="sidebar__new" onClick={onNewChat} aria-label="Start a new chat">
          + New
        </button>
      </div>
      <nav className="sidebar__list">
        {conversations.length === 0 && (
          <p className="sidebar__empty">No conversations yet</p>
        )}
        {conversations.map((conv) => (
          <button
            key={conv.id}
            className={
              'sidebar__item' + (conv.id === activeId ? ' sidebar__item--active' : '')
            }
            onClick={() => onSelect(conv.id)}
            title={conversationLabel(conv)}
          >
            <span className="sidebar__item-label">{conversationLabel(conv)}</span>
          </button>
        ))}
      </nav>
    </aside>
  );
}
