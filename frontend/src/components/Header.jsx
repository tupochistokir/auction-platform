function Header({
  page,
  goToCatalog,
  goToSell,
  goToProfile,
  goToFavorites,
  authUser,
  currentUserName,
  avatarUrl,
  onLogout,
}) {
  const displayInitial = (currentUserName || "U").slice(0, 1);

  return (
    <header className="topbar">
      <button
        className="brand-mark"
        type="button"
        onClick={goToCatalog}
        aria-label="Перейти на главную страницу"
      >
        <p className="eyebrow">Аукционная second-hand платформа</p>
        <h1>Vintage Market</h1>
        <div className="brand-divider" aria-hidden="true">
          <span />
          <i>✦</i>
          <span />
        </div>
      </button>

      <div className="topbar-ornament" aria-hidden="true">
        <span />
        <i>VM</i>
        <span />
      </div>

      <div className="topbar-actions">
        <button
          className={`nav-btn ${page === "catalog" ? "active" : ""}`}
          onClick={goToCatalog}
          type="button"
        >
          Каталог
        </button>

        <button
          className={`nav-btn ${page === "sell" ? "active" : ""}`}
          onClick={goToSell}
          type="button"
        >
          Продать товар
        </button>

        {authUser && (
          <button
            className={`nav-btn ${page === "favorites" ? "active" : ""}`}
            onClick={goToFavorites}
            type="button"
          >
            Избранное
          </button>
        )}

        <button
          className={`nav-btn ${page === "profile" ? "active" : ""}`}
          onClick={goToProfile}
          type="button"
        >
          {authUser ? "Кабинет" : "Войти"}
        </button>

        {authUser && (
          <div className="user-pill">
            <span className="user-avatar">
              {avatarUrl ? <img src={avatarUrl} alt={currentUserName} /> : displayInitial}
            </span>
            <span>{currentUserName}</span>
            <button className="logout-btn" type="button" onClick={onLogout}>
              Выйти
            </button>
          </div>
        )}
      </div>
    </header>
  );
}

export default Header;
