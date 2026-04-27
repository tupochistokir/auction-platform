const formatMoney = (value) =>
  typeof value === "number" ? `${value.toFixed(2)} ₽` : "—";

const statusLabel = (status) => {
  const labels = {
    active: "Активен",
    finished: "Завершён",
    pending: "Ожидает",
    accepted: "Принят",
    rejected: "Отклонён",
    counteroffer: "Контроффер",
  };
  return labels[status] || status || "—";
};

const recommendationLabel = (recommendation) => {
  const labels = {
    accept: "модель советует принять",
    reject: "модель советует отклонить",
    counteroffer: "модель советует контроффер",
  };
  return labels[recommendation] || "нет рекомендации";
};

function StatCard({ label, value }) {
  return (
    <div className="profile-stat-card">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function AuctionMiniCard({ auction, onOpen }) {
  return (
    <button className="profile-auction-card" type="button" onClick={() => onOpen(auction)}>
      <div className="profile-auction-image">
        {auction.image_url && <img src={auction.image_url} alt={auction.title} />}
      </div>
      <div>
        <span>{auction.brand}</span>
        <strong>{auction.title}</strong>
        <p>
          {formatMoney(auction.current_price)} · {statusLabel(auction.status)}
        </p>
      </div>
    </button>
  );
}

function ProfilePage({
  currentUserName,
  profileMode,
  setProfileMode,
  profileData,
  profileLoading,
  profileError,
  handleSelectAuction,
  handleOfferDecision,
  goToSell,
}) {
  const buyerStats = profileData?.buyer?.stats || {};
  const sellerStats = profileData?.seller?.stats || {};
  const buyerBids = profileData?.buyer?.bids || [];
  const sentOffers = profileData?.buyer?.offers || [];
  const sellerListings = profileData?.seller?.listings || [];
  const incomingOffers = profileData?.seller?.incoming_offers || [];

  return (
    <>
      <section className="hero-banner profile-hero">
        <div>
          <p className="hero-label">Личный кабинет</p>
          <h2>{currentUserName || "Пользователь"}</h2>
          <p>
            Единый аккаунт для покупок и продаж: ставки, офферы, мои лоты и
            решения продавца находятся в одном месте.
          </p>
        </div>
      </section>

      {profileError && <div className="error-box">{profileError}</div>}
      {profileLoading && <div className="empty-box">Загружаем кабинет...</div>}

      <div className="profile-shell">
        <aside className="profile-sidebar">
          <div className="profile-avatar">{(currentUserName || "U").slice(0, 1)}</div>
          <h3>{currentUserName}</h3>
          <p>Покупатель и продавец</p>

          <div className="profile-mode-toggle">
            <button
              className={profileMode === "buyer" ? "active" : ""}
              onClick={() => setProfileMode("buyer")}
              type="button"
            >
              Покупатель
            </button>
            <button
              className={profileMode === "seller" ? "active" : ""}
              onClick={() => setProfileMode("seller")}
              type="button"
            >
              Продавец
            </button>
          </div>

          <button className="primary-btn full" type="button" onClick={goToSell}>
            Разместить товар
          </button>
        </aside>

        <main className="profile-content">
          {profileMode === "buyer" ? (
            <>
              <div className="profile-stats-grid">
                <StatCard label="Аукционы со ставками" value={buyerStats.active_bids || 0} />
                <StatCard label="Я лидирую" value={buyerStats.leading_bids || 0} />
                <StatCard label="Отправлено офферов" value={buyerStats.sent_offers || 0} />
                <StatCard label="Офферы ждут ответа" value={buyerStats.pending_offers || 0} />
              </div>

              <section className="profile-panel">
                <div className="panel-header">
                  <h3>Мои ставки</h3>
                </div>

                <div className="profile-list-grid">
                  {buyerBids.map((item) => (
                    <div className="profile-bid-card" key={item.auction.id}>
                      <AuctionMiniCard auction={item.auction} onOpen={handleSelectAuction} />
                      <div className="profile-row">
                        <span>Моя последняя ставка</span>
                        <strong>{formatMoney(item.my_last_bid.amount)}</strong>
                      </div>
                      <div className={`profile-status ${item.is_leading ? "good" : "warn"}`}>
                        {item.is_leading ? "Вы лидируете" : "Ставку перебили"}
                      </div>
                    </div>
                  ))}

                  {!buyerBids.length && (
                    <div className="empty-box">Ты пока не делал ставки</div>
                  )}
                </div>
              </section>

              <section className="profile-panel">
                <div className="panel-header">
                  <h3>Мои офферы</h3>
                </div>

                <div className="profile-list-grid">
                  {sentOffers.map((item) => (
                    <div className="profile-offer-card" key={item.offer.id}>
                      <AuctionMiniCard auction={item.auction} onOpen={handleSelectAuction} />
                      <div className="profile-row">
                        <span>Оффер</span>
                        <strong>{formatMoney(item.offer.amount)}</strong>
                      </div>
                      <p>
                        {statusLabel(item.offer.status)} ·{" "}
                        {recommendationLabel(item.offer.recommendation)}
                      </p>
                    </div>
                  ))}

                  {!sentOffers.length && (
                    <div className="empty-box">Ты пока не отправлял офферы</div>
                  )}
                </div>
              </section>
            </>
          ) : (
            <>
              <div className="profile-stats-grid">
                <StatCard label="Всего лотов" value={sellerStats.listings || 0} />
                <StatCard label="Активные" value={sellerStats.active_listings || 0} />
                <StatCard label="Завершённые" value={sellerStats.finished_listings || 0} />
                <StatCard label="Ждут решения" value={sellerStats.pending_offers || 0} />
              </div>

              <section className="profile-panel">
                <div className="panel-header">
                  <h3>Мои объявления</h3>
                </div>

                <div className="profile-list-grid">
                  {sellerListings.map((auction) => (
                    <div className="profile-seller-card" key={auction.id}>
                      <AuctionMiniCard auction={auction} onOpen={handleSelectAuction} />
                      <div className="profile-row">
                        <span>Входящих офферов</span>
                        <strong>{auction.offers?.length || 0}</strong>
                      </div>
                      <div className="profile-row">
                        <span>Прогноз финала</span>
                        <strong>{formatMoney(auction.expected_final_price)}</strong>
                      </div>
                    </div>
                  ))}

                  {!sellerListings.length && (
                    <div className="empty-box">У тебя пока нет опубликованных лотов</div>
                  )}
                </div>
              </section>

              <section className="profile-panel">
                <div className="panel-header">
                  <h3>Входящие офферы</h3>
                </div>

                <div className="profile-offers-table">
                  {incomingOffers.map((item) => (
                    <div className="profile-offer-row" key={item.offer.id}>
                      <div>
                        <strong>{item.auction.title}</strong>
                        <p>
                          {item.offer.user} предлагает {formatMoney(item.offer.amount)}
                        </p>
                        <p>
                          {statusLabel(item.offer.status)} ·{" "}
                          {recommendationLabel(item.offer.recommendation)}
                        </p>
                      </div>

                      <div className="profile-offer-actions">
                        {item.offer.status === "pending" ? (
                          <>
                            <button
                              className="secondary-btn"
                              type="button"
                              onClick={() =>
                                handleOfferDecision(
                                  item.auction.id,
                                  item.offer.id,
                                  "reject"
                                )
                              }
                            >
                              Отклонить
                            </button>
                            <button
                              className="secondary-btn"
                              type="button"
                              onClick={() =>
                                handleOfferDecision(
                                  item.auction.id,
                                  item.offer.id,
                                  "counteroffer",
                                  item.offer.counter_amount
                                )
                              }
                            >
                              Контроффер
                            </button>
                            <button
                              className="primary-btn"
                              type="button"
                              onClick={() =>
                                handleOfferDecision(
                                  item.auction.id,
                                  item.offer.id,
                                  "accept"
                                )
                              }
                            >
                              Принять
                            </button>
                          </>
                        ) : (
                          <span className="profile-status good">
                            Решение сохранено
                          </span>
                        )}
                      </div>
                    </div>
                  ))}

                  {!incomingOffers.length && (
                    <div className="empty-box">Входящих офферов пока нет</div>
                  )}
                </div>
              </section>
            </>
          )}
        </main>
      </div>
    </>
  );
}

export default ProfilePage;
