type SidebarProps = {
  onNewAnalysis: () => void;
};

export function Sidebar({ onNewAnalysis }: SidebarProps) {
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
        <div className="history-wrapper" />
      </nav>

      <div className="profile">
        <span className="avatar">DA</span>
        <div><strong>Demo Analyst</strong><small>Investment team</small></div>
      </div>
    </aside>
  );
}
