function Header({ page, setPage }) {
  return (
    <header className="topbar">
      <div>
        <p className="eyebrow">Аукционная second-hand платформа</p>
        <h1>Vintage Market</h1>
      </div>

      <div className="topbar-actions">
        <button
          className={`nav-btn ${page === "catalog" ? "active" : ""}`}
          onClick={() => setPage("catalog")}
        >
          Каталог
        </button>

        <button
          className={`nav-btn ${page === "sell" ? "active" : ""}`}
          onClick={() => setPage("sell")}
        >
          Продать товар
        </button>

        <button className="secondary-btn">Профиль</button>
      </div>
    </header>
  );
}

export default Header;