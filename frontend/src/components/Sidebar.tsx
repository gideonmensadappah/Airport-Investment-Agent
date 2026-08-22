import type { LocalChat } from "../types/chat";

type SidebarProps = {
  activeChatId: string;
  chats: LocalChat[];
  onNewAnalysis: () => void;
  onSelectChat: (chatId: string) => void;
};

const dateFormatter = new Intl.DateTimeFormat("en", {
  month: "short",
  day: "numeric",
});

export function Sidebar({
  activeChatId,
  chats,
  onNewAnalysis,
  onSelectChat,
}: SidebarProps) {
  return (
    <aside className="sidebar">
      <div className="brand">
        <span className="brand-mark">A</span>
        <div><strong>AirIntel</strong><small>Investment Agent</small></div>
      </div>

      <button className="new-button" type="button" onClick={onNewAnalysis}>
        <b>＋</b> New analysis
      </button>

      <nav aria-label="Recent chats">
        <p className="nav-label">Chats</p>
        <div className="history-wrapper">
          {chats.map(chat => (
            <button
              className={`history-item${chat.id === activeChatId ? " active" : ""}`}
              type="button"
              key={chat.id}
              aria-current={chat.id === activeChatId ? "page" : undefined}
              onClick={() => onSelectChat(chat.id)}
            >
              <span className="history-icon" aria-hidden="true">⌁</span>
              <span>
                <strong>{chat.title}</strong>
                <small>{dateFormatter.format(new Date(chat.updatedAt))}</small>
              </span>
            </button>
          ))}
        </div>
      </nav>

      <div className="profile">
        <span className="avatar">DA</span>
        <div><strong>Demo Analyst</strong><small>Investment team</small></div>
      </div>
    </aside>
  );
}
