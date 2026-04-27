function Header({ page, setPage, currentUserName, setCurrentUserName }) {
  return (
    <header className="topbar">
      <div>
        <p className="eyebrow">Аукционная second-hand платформа</p>
        <h1>Vintage Market</h1>
      </div>

      <div className="topbar-actions">
        <div className="account-switcher">
          <span>Аккаунт</span>
          <input
            value={currentUserName}
            onChange={(e) => setCurrentUserName(e.target.value)}
          />
        </div>

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

        <button
          className={`nav-btn ${page === "profile" ? "active" : ""}`}
          onClick={() => setPage("profile")}
        >
          Профиль
        </button>
      </div>
    </header>
  );
}

export default Header;
