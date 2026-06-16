import { useMemo, useState } from "react";
import {
  findSecondStoreForAuction,
  isSecondStoreAuction,
  secondStores,
} from "../data/secondStores";

const formatMoney = (value) => {
  const number = Number(value);
  return Number.isFinite(number) ? `${Math.round(number).toLocaleString("ru-RU")} ₽` : "-";
};

const formatRemainingTime = (endTime, status) => {
  if (status !== "active") return "";
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

function SecondStoresPage({ auctions, loading, error, handleSelectAuction }) {
  const [selectedStoreId, setSelectedStoreId] = useState(secondStores[0]?.id || "");

  const { lotsByStore, secondStoreLots } = useMemo(() => {
    const groupedLots = secondStores.reduce((acc, store) => {
      acc[store.id] = [];
      return acc;
    }, {});
    const lots = auctions.filter(isSecondStoreAuction);

    lots.forEach((auction) => {
      const store = findSecondStoreForAuction(auction);
      if (store && groupedLots[store.id]) {
        groupedLots[store.id].push(auction);
      }
    });

    return { lotsByStore: groupedLots, secondStoreLots: lots };
  }, [auctions]);

  const selectedStore =
    secondStores.find((store) => store.id === selectedStoreId) || secondStores[0];
  const selectedLots = selectedStore ? lotsByStore[selectedStore.id] || [] : [];

  return (
    <>
      <section className="hero-banner second-stores-hero">
        <div>
          <p className="hero-label">Секонды и партнёрские витрины</p>
          <h2>Эксклюзивные лоты из секондов в формате аукциона</h2>
          <p>
            Магазин получает отдельную витрину, а его товары параллельно остаются в
            общем каталоге. Для покупателя это честный доступ к редким вещам, для
            секонда — дополнительный канал продаж и рекламы.
          </p>
        </div>
      </section>

      {error && <div className="error-box">{error}</div>}

      <section className="second-partner-strip">
        <div>
          <span>Для секондов</span>
          <strong>витрина магазина плюс общий поток покупателей</strong>
        </div>
        <div>
          <span>Для покупателей</span>
          <strong>дропы, ставки и прозрачная карточка лота</strong>
        </div>
        <div>
          <span>Для запуска</span>
          <strong>пилотные магазины можно подключать без переделки каталога</strong>
        </div>
      </section>

      <section className="second-stores-layout">
        <aside className="second-store-list" aria-label="Список секондов">
          <div className="section-heading">
            <p className="hero-label">Каталог секондов</p>
            <h3>Партнёрские витрины</h3>
          </div>

          {secondStores.map((store) => {
            const storeLots = lotsByStore[store.id] || [];
            const isActive = selectedStore?.id === store.id;

            return (
              <article key={store.id} className={`second-store-card ${isActive ? "active" : ""}`}>
                <button type="button" onClick={() => setSelectedStoreId(store.id)}>
                  <span>{store.district}</span>
                  <strong>{store.name}</strong>
                  <small>{store.concept}</small>
                </button>

                <div className="second-store-card-footer">
                  <span>{storeLots.length} лотов</span>
                  <a href={store.mapUrl} target="_blank" rel="noreferrer">
                    Посмотреть секонд на карте
                  </a>
                </div>
              </article>
            );
          })}
        </aside>

        <main className="second-store-showcase">
          <div className="second-store-profile">
            <div>
              <p className="hero-label">Выбранный секонд</p>
              <h3>{selectedStore?.name}</h3>
              <p>{selectedStore?.concept}</p>
            </div>

            <div className="second-store-facts">
              <span>{selectedStore?.dropSchedule}</span>
              <span>{selectedStore?.auctionFormat}</span>
              <span>{selectedStore?.address}</span>
            </div>

            <a className="store-map-button" href={selectedStore?.mapUrl} target="_blank" rel="noreferrer">
              Посмотреть секонд на карте
            </a>
          </div>

          <div className="second-store-note">
            Товары партнёров не отделяются от общего рынка: лот виден в этой витрине и в
            обычном каталоге одновременно. В дальнейшем здесь можно добавить расписание
            завозов, карточку магазина, рейтинг и подборки «только в аукционе».
          </div>

          {loading ? (
            <div className="empty-box">Загружаем лоты секондов...</div>
          ) : selectedLots.length ? (
            <div className="market-grid second-store-lots">
              {selectedLots.map((auction) => {
                const image = auction.image_urls?.[0] || auction.image_url;

                return (
                  <button
                    key={auction.id}
                    className="market-card second-lot-card"
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
                      {auction.status === "active" && (
                        <div className="market-time-badge">
                          {formatRemainingTime(auction.end_time, auction.status)}
                        </div>
                      )}
                    </div>

                    <div className="market-card-body">
                      <p className="market-brand">{auction.brand || "unknown"}</p>
                      <h4>{auction.title}</h4>

                      <div className="market-card-meta">
                        <span>{selectedStore?.name}</span>
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
          ) : (
            <div className="empty-box second-empty-box">
              <h4>У этого секонда пока нет подключённых лотов</h4>
              <p>
                После подключения магазина его товары появятся здесь и в общем каталоге.
                Это удобно для пилота: партнёр получает отдельную страницу, а покупатель
                всё равно видит вещи в общей выдаче.
              </p>
            </div>
          )}

          <div className="second-total-line">
            Сейчас к партнёрским витринам относится {secondStoreLots.length} лотов.
          </div>
        </main>
      </section>
    </>
  );
}

export default SecondStoresPage;
