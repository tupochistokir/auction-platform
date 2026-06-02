import { useState } from "react";

const formatMoney = (value) => {
  const number = Number(value);
  return Number.isFinite(number) ? `${Math.round(number).toLocaleString("ru-RU")} ₽` : "—";
};

const statusLabel = (status) => {
  const labels = {
    pending: "Ждёт решения продавца",
    counteroffer: "Встречная цена отправлена",
    accepted: "Принят",
    rejected: "Отклонён",
  };
  return labels[status] || status || "—";
};

const offerStageLabel = (offer, role = "buyer") => {
  if (offer.status === "pending") {
    return role === "seller" ? "Новый оффер покупателя" : "У продавца на рассмотрении";
  }
  if (offer.status === "counteroffer") {
    return role === "seller"
      ? "Встречная цена отправлена покупателю"
      : "Продавец предложил встречную цену";
  }
  if (offer.status === "accepted") return "Сделка принята";
  if (offer.status === "rejected") return "Отклонено";
  return statusLabel(offer.status);
};

function OfferAuctionCard({ auction, onOpen }) {
  return (
    <button className="offers-auction-card" type="button" onClick={() => onOpen(auction)}>
      <div className="offers-auction-image">
        {auction.image_url ? <img src={auction.image_url} alt={auction.title} /> : null}
      </div>
      <div>
        <span>{auction.brand || "Бренд не указан"}</span>
        <strong>{auction.title}</strong>
        <p>{formatMoney(auction.current_price)} · {auction.status === "active" ? "активен" : "завершён"}</p>
      </div>
    </button>
  );
}

function IncomingOfferCard({ item, handleSelectAuction, handleOfferDecision }) {
  const [counterAmount, setCounterAmount] = useState(item.offer.counter_amount || "");
  const [message, setMessage] = useState("");
  const pending = item.offer.status === "pending";

  const decide = async (action) => {
    try {
      const result = await handleOfferDecision(
        item.auction.id,
        item.offer.id,
        action,
        action === "counteroffer" ? counterAmount : null
      );

      if (result) {
        setMessage(
          action === "accept"
            ? "Оффер принят. Торги завершены по цене покупателя."
            : action === "counteroffer"
            ? "Встречная цена отправлена покупателю в исходящие офферы."
            : "Оффер отклонён."
        );
      }
    } catch (error) {
      setMessage(error.message || "Не удалось сохранить решение");
    }
  };

  return (
    <article className={`offers-card offer-stage-${item.offer.status}`}>
      <OfferAuctionCard auction={item.auction} onOpen={handleSelectAuction} />

      <div className="offers-card-body">
        <div className="offers-main-row">
          <span>Покупатель</span>
          <strong>{item.offer.user}</strong>
        </div>
        <div className="offers-main-row">
          <span>Оффер</span>
          <strong>{formatMoney(item.offer.amount)}</strong>
        </div>
        <div className="offer-stage-pill">{offerStageLabel(item.offer, "seller")}</div>
        <p className="offer-decision-note">
          Оффер — цена покупателя за досрочную покупку. Контроффер — встречная цена
          продавца, которую покупатель увидит в своих исходящих офферах.
        </p>
        {item.offer.counter_amount ? (
          <p className="offer-decision-note">
            Последняя встречная цена: <strong>{formatMoney(item.offer.counter_amount)}</strong>
          </p>
        ) : null}
        {message ? <div className="success-box compact">{message}</div> : null}
      </div>

      {pending ? (
        <div className="offers-actions">
          <div className="field counteroffer-field">
            <label>Встречная цена</label>
            <input
              type="number"
              step="1"
              value={counterAmount}
              onChange={(event) => setCounterAmount(event.target.value)}
              placeholder="Например 2500"
            />
          </div>
          <button className="secondary-btn" type="button" onClick={() => decide("reject")}>
            Отклонить
          </button>
          <button
            className="secondary-btn"
            type="button"
            disabled={!counterAmount}
            onClick={() => decide("counteroffer")}
          >
            Отправить встречную
          </button>
          <button className="primary-btn" type="button" onClick={() => decide("accept")}>
            Принять
          </button>
        </div>
      ) : null}
    </article>
  );
}

function OutgoingOfferCard({ item, handleSelectAuction, handleBuyerOfferDecision }) {
  const [message, setMessage] = useState("");
  const offer = item.offer;
  const canAnswer = offer.status === "counteroffer" && offer.counter_amount;

  const answer = async (action) => {
    try {
      await handleBuyerOfferDecision(item.auction.id, offer.id, action);
      setMessage(
        action === "accept"
          ? "Встречная цена принята. Лот завершён по цене продавца."
          : "Встречная цена отклонена."
      );
    } catch (error) {
      setMessage(error.message || "Не удалось сохранить ответ");
    }
  };

  return (
    <article className={`offers-card offer-stage-${offer.status}`}>
      <OfferAuctionCard auction={item.auction} onOpen={handleSelectAuction} />

      <div className="offers-card-body">
        <div className="offers-main-row">
          <span>Мой оффер</span>
          <strong>{formatMoney(offer.amount)}</strong>
        </div>
        {offer.counter_amount ? (
          <div className="offers-main-row">
            <span>Контроффер продавца</span>
            <strong>{formatMoney(offer.counter_amount)}</strong>
          </div>
        ) : null}
        <div className="offer-stage-pill">{offerStageLabel(offer, "buyer")}</div>
        <p className="offer-decision-note">
          Исходящий оффер видит продавец. Если продавец отправит контроффер,
          решение снова переходит к покупателю.
        </p>
        {message ? <div className="success-box compact">{message}</div> : null}
      </div>

      {canAnswer ? (
        <div className="offers-actions compact-actions">
          <button className="primary-btn" type="button" onClick={() => answer("accept")}>
            Принять встречную цену
          </button>
          <button className="secondary-btn" type="button" onClick={() => answer("reject")}>
            Отклонить
          </button>
        </div>
      ) : null}
    </article>
  );
}

function OffersPage({
  profileData,
  profileLoading,
  profileError,
  handleSelectAuction,
  handleOfferDecision,
  handleBuyerOfferDecision,
  goToProfile,
}) {
  const incomingOffers = profileData?.seller?.incoming_offers || [];
  const outgoingOffers = profileData?.buyer?.offers || [];

  return (
    <>
      <section className="hero-banner offers-hero">
        <div>
          <p className="hero-label">Офферы</p>
          <h2>Входящие и исходящие предложения</h2>
          <p>
            Покупатель отправляет оффер, продавец принимает, отклоняет или предлагает
            встречную цену. Все решения по цене собраны здесь.
          </p>
        </div>
      </section>

      {profileError ? <div className="error-box">{profileError}</div> : null}
      {profileLoading ? <div className="empty-box">Загружаем офферы...</div> : null}

      <div className="offers-page-grid">
        <section className="profile-panel offers-column">
          <div className="panel-header">
            <h3>Входящие продавца</h3>
            <span>{incomingOffers.length}</span>
          </div>
          <div className="offers-list">
            {incomingOffers.map((item) => (
              <IncomingOfferCard
                key={item.offer.id}
                item={item}
                handleSelectAuction={handleSelectAuction}
                handleOfferDecision={handleOfferDecision}
              />
            ))}
            {!incomingOffers.length ? (
              <div className="empty-box compact">Входящих офферов пока нет</div>
            ) : null}
          </div>
        </section>

        <section className="profile-panel offers-column">
          <div className="panel-header">
            <h3>Исходящие покупателя</h3>
            <span>{outgoingOffers.length}</span>
          </div>
          <div className="offers-list">
            {outgoingOffers.map((item) => (
              <OutgoingOfferCard
                key={item.offer.id}
                item={item}
                handleSelectAuction={handleSelectAuction}
                handleBuyerOfferDecision={handleBuyerOfferDecision}
              />
            ))}
            {!outgoingOffers.length ? (
              <div className="empty-box compact">Исходящих офферов пока нет</div>
            ) : null}
          </div>
        </section>
      </div>

      <button className="secondary-btn offers-back-btn" type="button" onClick={goToProfile}>
        Вернуться в кабинет
      </button>
    </>
  );
}

export default OffersPage;
