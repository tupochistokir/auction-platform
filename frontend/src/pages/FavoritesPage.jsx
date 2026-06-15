const formatMoney = (value) => {
  const number = Number(value);
  return Number.isFinite(number) ? `${Math.round(number).toLocaleString("ru-RU")} ₽` : "—";
};

const formatRemainingTime = (endTime, status) => {
  if (status !== "active") return "завершён";
  if (!endTime) return "срок не задан";

  const diff = new Date(endTime).getTime() - Date.now();
  if (!Number.isFinite(diff) || diff <= 0) return "завершается";

  const totalMinutes = Math.floor(diff / 60000);
  const days = Math.floor(totalMinutes / 1440);
  const hours = Math.floor((totalMinutes % 1440) / 60);
  const minutes = totalMinutes % 60;

  if (days > 0) return `${days}д ${hours}ч`;
  if (hours > 0) return `${hours}ч ${minutes}м`;
  return `${Math.max(minutes, 1)}м`;
};

function FavoritesPage({
  favorites,
  loading,
  error,
  handleSelectAuction,
  goToCatalog,
}) {
  const favoriteLots = favorites || [];

  return (
    <>
      <section className="hero-banner favorites-hero">
        <div>
          <p className="hero-label">Избранное</p>
          <h2>Сохранённые лоты</h2>
          <p>
            Здесь находятся товары, которые ты отметил в карточке. Избранное
            отделено от кабинета, чтобы покупки и управление аккаунтом не смешивались.
          </p>
        </div>
      </section>

      {error && <div className="error-box">{error}</div>}
      {loading && <div className="empty-box">Загружаем избранное...</div>}

      {!loading && !favoriteLots.length && (
        <section className="favorites-empty-panel">
          <h3>Пока ничего не сохранено</h3>
          <p>Открой карточку товара и нажми «В избранное», чтобы лот появился здесь.</p>
          <button className="primary-btn" type="button" onClick={goToCatalog}>
            Перейти в каталог
          </button>
        </section>
      )}

      {!!favoriteLots.length && (
        <div className="market-grid favorites-grid">
          {favoriteLots.map((item) => {
            const auction = item.auction;
            const image = auction.image_urls?.[0] || auction.image_url;

            return (
              <button
                key={auction.id}
                className="market-card"
                type="button"
                onClick={() => handleSelectAuction(auction)}
              >
                <div className="market-card-image">
                  {image ? (
                    <img src={image} alt={auction.title} className="market-card-img" />
                  ) : (
                    <div className="market-card-placeholder">KLOS</div>
                  )}

                  <div className="market-badge">
                    {auction.status === "active" ? "Аукцион" : "Завершён"}
                  </div>
                  <div className="market-time-badge">
                    {formatRemainingTime(auction.end_time, auction.status)}
                  </div>
                </div>

                <div className="market-card-body">
                  <p className="market-brand">{auction.brand || "unknown"}</p>
                  <h4>{auction.title}</h4>

                  <div className="market-card-meta">
                    <span>{auction.questionnaire?.subcategory || auction.questionnaire?.category || "Лот"}</span>
                    <span>шаг {formatMoney(auction.recommended_bid_step)}</span>
                  </div>

                  <div className="market-price-row">
                    <strong>{formatMoney(auction.current_price)}</strong>
                    <span>{auction.status === "active" ? "идут торги" : "лот закрыт"}</span>
                  </div>
                </div>
              </button>
            );
          })}
        </div>
      )}
    </>
  );
}

export default FavoritesPage;
