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

const recoveryQuestions = [
  { value: "first_teacher_last_name", label: "Фамилия первого учителя" },
  { value: "pet_name", label: "Кличка первого питомца" },
  { value: "childhood_street", label: "Улица детства" },
  { value: "favorite_book", label: "Любимая книга" },
  { value: "birth_city", label: "Город рождения" },
];

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
  const isRecover = mode === "recover";

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
          <button
            className={mode === "recover" ? "active" : ""}
            type="button"
            onClick={() => setMode("recover")}
          >
            Восстановить
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

            <div className="field">
              <label>Вопрос для восстановления</label>
              <select
                name="recovery_question"
                value={form.recovery_question}
                onChange={onChange}
                required
              >
                {recoveryQuestions.map((question) => (
                  <option key={question.value} value={question.value}>
                    {question.label}
                  </option>
                ))}
              </select>
            </div>

            <div className="field">
              <label>Ответ на вопрос</label>
              <input
                name="recovery_answer"
                value={form.recovery_answer}
                onChange={onChange}
                placeholder="Ответ пригодится, если забудете пароль"
                required
              />
            </div>
          </>
        ) : isRecover ? (
          <>
            <div className="field">
              <label>Email аккаунта</label>
              <input
                name="email"
                type="email"
                value={form.email}
                onChange={onChange}
                placeholder="mail@example.ru"
                required
              />
            </div>

            <div className="field">
              <label>Вопрос для восстановления</label>
              <select
                name="recovery_question"
                value={form.recovery_question}
                onChange={onChange}
                required
              >
                {recoveryQuestions.map((question) => (
                  <option key={question.value} value={question.value}>
                    {question.label}
                  </option>
                ))}
              </select>
            </div>

            <div className="field">
              <label>Ответ</label>
              <input
                name="recovery_answer"
                value={form.recovery_answer}
                onChange={onChange}
                placeholder="Тот же ответ, что при регистрации"
                required
              />
            </div>

            <div className="field">
              <label>Новый пароль</label>
              <input
                name="new_password"
                type="password"
                value={form.new_password}
                onChange={onChange}
                placeholder="Минимум 6 символов"
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

        {!isRecover && (
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
        )}

        {error && <div className="error-box">{error}</div>}

        <button className="primary-btn full-width" type="submit" disabled={loading}>
          {loading
            ? "Проверяем..."
            : isRegister
            ? "Создать аккаунт"
            : isRecover
            ? "Сменить пароль"
            : "Войти в кабинет"}
        </button>
      </form>
    </section>
  );
}

export default AuthPage;
