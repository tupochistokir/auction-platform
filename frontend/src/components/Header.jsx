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
    <header className={`topbar ${authUser ? "topbar-authenticated" : "topbar-guest"}`}>
      <div className="topbar-main-row">
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

        <nav className="primary-nav" aria-label="Основная навигация">
          <button
            className={`nav-btn ${page === "catalog" ? "active" : ""}`}
            onClick={goToCatalog}
            type="button"
          >
            Каталог
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
            className={`nav-btn ${page === "sell" ? "active" : ""}`}
            onClick={goToSell}
            type="button"
          >
            Продать товар
          </button>
        </nav>
      </div>

      <div className="account-bar" aria-label={authUser ? "Личный кабинет" : "Вход"}>
        {authUser ? (
          <>
            <div className="account-id">
              <span className="user-avatar">
                {avatarUrl ? <img src={avatarUrl} alt={currentUserName} /> : displayInitial}
              </span>
              <span className="account-name">{currentUserName}</span>
            </div>

            <button
              className={`nav-btn account-nav-btn ${page === "profile" ? "active" : ""}`}
              onClick={goToProfile}
              type="button"
            >
              Кабинет
            </button>

            <button className="nav-btn account-nav-btn" onClick={goToProfile} type="button">
              Редактировать
            </button>

            <button className="logout-btn" type="button" onClick={onLogout}>
              Выйти
            </button>
          </>
        ) : (
          <button
            className={`nav-btn account-nav-btn ${page === "profile" ? "active" : ""}`}
            onClick={goToProfile}
            type="button"
          >
            Войти
          </button>
        )}
      </div>
    </header>
  );
}

export default Header;
