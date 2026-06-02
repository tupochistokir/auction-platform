const authCopy = {
  profile: {
    label: "Личный кабинет",
    title: "Войдите, чтобы открыть кабинет",
    text: "После входа здесь будут ставки, офферы, опубликованные товары и решения продавца.",
  },
  sell: {
    label: "Продажа товара",
    title: "Войдите, чтобы опубликовать лот",
    text: "Аккаунт связывает товар с продавцом, поэтому офферы и контрофферы попадают в нужный кабинет.",
  },
  favorites: {
    label: "Избранное",
    title: "Войдите, чтобы открыть избранное",
    text: "Сохранённые лоты доступны только в аккаунте, чтобы список не терялся после перезагрузки.",
  },
};

function AuthPage({
  mode,
  setMode,
  form,
  onChange,
  onSubmit,
  loading,
  error,
  variant = "profile",
}) {
  const copy = authCopy[variant] || authCopy.profile;
  const isRegister = mode === "register";

  return (
    <section className="auth-shell">
      <div className="auth-hero">
        <p className="hero-label">{copy.label}</p>
        <h2>{copy.title}</h2>
        <p>{copy.text}</p>
      </div>

      <form className="auth-card" onSubmit={onSubmit}>
        <div className="auth-tabs">
          <button
            className={mode === "login" ? "active" : ""}
            type="button"
            onClick={() => setMode("login")}
          >
            Вход
          </button>
          <button
            className={mode === "register" ? "active" : ""}
            type="button"
            onClick={() => setMode("register")}
          >
            Регистрация
          </button>
        </div>

        {isRegister ? (
          <>
            <div className="field">
              <label>Имя в кабинете</label>
              <input
                name="display_name"
                value={form.display_name}
                onChange={onChange}
                placeholder="Например: Кирилл"
              />
            </div>

            <div className="field">
              <label>Логин</label>
              <input
                name="username"
                value={form.username}
                onChange={onChange}
                placeholder="kirill"
                required
              />
            </div>

            <div className="field">
              <label>Email</label>
              <input
                name="email"
                type="email"
                value={form.email}
                onChange={onChange}
                placeholder="mail@example.ru"
                required
              />
            </div>
          </>
        ) : (
          <div className="field">
            <label>Логин или email</label>
            <input
              name="identifier"
              value={form.identifier}
              onChange={onChange}
              placeholder="kirill или mail@example.ru"
              required
            />
          </div>
        )}

        <div className="field">
          <label>Пароль</label>
          <input
            name="password"
            type="password"
            value={form.password}
            onChange={onChange}
            placeholder="Минимум 6 символов"
            required
          />
        </div>

        {error && <div className="error-box">{error}</div>}

        <button className="primary-btn full-width" type="submit" disabled={loading}>
          {loading ? "Проверяем..." : isRegister ? "Создать аккаунт" : "Войти в кабинет"}
        </button>
      </form>
    </section>
  );
}

export default AuthPage;
