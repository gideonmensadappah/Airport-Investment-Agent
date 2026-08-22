type HeaderProps = {
  title?: string | null;
};

export function Header({ title }: HeaderProps) {
  return (
    <header className="topbar">
      <div>
        <span className="mobile-brand">AirIntel</span>
        <h1>{title ?? "Airport investment analysis"}</h1>
        <p>Deterministic comparison · MVP</p>
      </div>
    </header>
  );
}
