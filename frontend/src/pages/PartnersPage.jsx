const partnerSteps = [
  {
    number: "01",
    title: "Отложите 5-10 лучших вещей из завоза",
    text: "Партнер выбирает позиции, которые в обычной продаже могут уйти слишком дешево или слишком быстро.",
  },
  {
    number: "02",
    title: "Мы рассчитаем стартовую и ожидаемую цену",
    text: "Платформа учитывает бренд, состояние, редкость, фото, анкету и будущие сигналы спроса.",
  },
  {
    number: "03",
    title: "Запустим онлайн-аукцион",
    text: "Лот попадает в обычный каталог и отдельную витрину секонда, чтобы магазин получил дополнительный поток внимания.",
  },
  {
    number: "04",
    title: "Если продали дороже вашей цены - делим дополнительную выручку",
    text: "Магазин заранее фиксирует желаемую цену. Все, что удалось заработать сверху, становится понятной мотивацией для сотрудничества.",
  },
  {
    number: "05",
    title: "Если не продали - вещь возвращается в обычную продажу",
    text: "Пилот не блокирует товар надолго: вещь можно вернуть на полку или снова выставить с другой стартовой ценой.",
  },
];

function PartnersPage({ goToSecondStores, goToSell }) {
  return (
    <>
      <section className="hero-banner partners-hero">
        <div>
          <p className="hero-label">Для партнеров</p>
          <h2>Онлайн-аукционы для лучших вещей из завоза</h2>
          <p>
            Секонд получает отдельную витрину на платформе, а самые сильные позиции продаются не по принципу
            "кто первый успел", а через честные ставки покупателей.
          </p>
        </div>
      </section>

      <section className="partners-value-row">
        <div>
          <span>Для магазина</span>
          <strong>дополнительная выручка без запуска собственного IT-продукта</strong>
        </div>
        <div>
          <span>Для покупателей</span>
          <strong>понятный доступ к редким вещам из конкретных секондов</strong>
        </div>
        <div>
          <span>Для пилота</span>
          <strong>можно начать с одного магазина и небольшой партии лотов</strong>
        </div>
      </section>

      <section className="partners-workflow">
        <div className="partners-workflow-head">
          <p className="hero-label">Схема сотрудничества</p>
          <h3>Пять простых шагов</h3>
          <p>
            Модель сделана так, чтобы партнеру было легко протестировать формат. Не нужно переносить весь
            ассортимент: достаточно выбрать несколько вещей, по которым есть шанс получить цену выше обычной.
          </p>
        </div>

        <div className="partners-steps-grid">
          {partnerSteps.map((step) => (
            <article className="partner-step-card" key={step.number}>
              <span>{step.number}</span>
              <h4>{step.title}</h4>
              <p>{step.text}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="partners-pilot-box">
        <div>
          <p className="hero-label">Пилотный формат</p>
          <h3>Почему секонду выгодно попробовать</h3>
          <p>
            Магазин не теряет обычный канал продаж. Если спрос высокий, аукцион помогает проверить реальную
            готовность покупателей платить больше. Если спрос слабый, товар возвращается в привычную продажу,
            а платформа получает данные для следующего запуска.
          </p>
        </div>

        <div className="partners-pilot-actions">
          <button className="primary-btn" type="button" onClick={goToSecondStores}>
            Открыть витрины секондов
          </button>
          <button className="secondary-btn" type="button" onClick={goToSell}>
            Добавить тестовый лот
          </button>
        </div>
      </section>
    </>
  );
}

export default PartnersPage;
