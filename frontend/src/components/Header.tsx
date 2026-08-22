type HeaderProps = {
  title?: string | null;
  onNewAnalysis: () => void;
};

export function Header({ title, onNewAnalysis }: HeaderProps) {
  return (
    <header className="topbar">
      <div>
        <span className="mobile-brand">AirIntel</span>
        <h1>{title ?? "Airport investment analysis"}</h1>
        <p>Deterministic comparison · MVP</p>
      </div>
      <button
        className="mobile-new-analysis"
        type="button"
        onClick={onNewAnalysis}
        aria-label="New analysis"
      >
        <span aria-hidden="true">＋</span> New
      </button>
    </header>
  );
}
