import { useEffect, useMemo, useState } from "react";

const formatMoney = (value) =>
  typeof value === "number" ? `${value.toFixed(2)} ₽` : "—";

const formatScore = (value) =>
  typeof value === "number" ? value.toFixed(4) : "—";

const formatDateTime = (value) => {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "—";
  return date.toLocaleString("ru-RU", {
    day: "2-digit",
    month: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
};

const getDecisionLabel = (decision) => {
  const labels = {
    accepted: "Оффер принят",
    counteroffer: "Продавец предложил контроффер",
    rejected: "Оффер отклонён",
    pending: "Ожидает решения продавца",
  };
  return labels[decision] || "Оффер обработан";
};

const getRecommendationLabel = (recommendation) => {
  const labels = {
    accept: "модель советует принять",
    counteroffer: "модель советует контроффер",
    reject: "модель советует отклонить",
  };
  return labels[recommendation] || "модель ждёт данных";
};

const getTradeInsight = (currentPrice, basePrice, expectedPrice, bidCount, pendingOffers) => {
  if (!bidCount && !pendingOffers) {
    return {
      buyer: "Для покупателя это ранняя стадия: цена ещё не проверена конкуренцией, поэтому минимальная ставка информативнее резкого повышения.",
      seller: "Для продавца спрос пока не подтверждён ставками. Имеет смысл смотреть на первые офферы и не завершать аукцион автоматически.",
    };
  }

  if (currentPrice < basePrice) {
    return {
      buyer: "Текущая цена ниже базовой оценки модели: для покупателя это зона потенциально выгодной ставки.",
      seller: "Цена ниже базовой оценки: продавцу рациональнее ждать, если нет сильного оффера выше порога ожидания.",
    };
  }

  if (currentPrice <= expectedPrice) {
    return {
      buyer: "Цена находится в рабочей зоне между базовой и прогнозной: ставка имеет смысл, если личная ценность товара выше текущей цены.",
      seller: "Торги идут в здоровой зоне: можно принимать только офферы, близкие к прогнозу финальной цены.",
    };
  }

  return {
    buyer: "Цена выше прогноза модели: для покупателя это зона перегрева, рекомендуемая ставка должна быть осторожной.",
    seller: "Цена уже выше прогноза: продавцу выгоднее поддерживать аукцион, а не принимать слабые офферы.",
  };
};

const getRemainingTime = (endTime, createdAt, now, status) => {
  if (!now) {
    return {
      label: "Синхронизация таймера",
      percent: 0,
      isFinished: status !== "active",
    };
  }

  if (!endTime) {
    return {
      label: "Время не задано",
      percent: 0,
      isFinished: status !== "active",
    };
  }

  const end = new Date(endTime).getTime();
  if (Number.isNaN(end)) {
    return {
      label: "Время не задано",
      percent: 0,
      isFinished: status !== "active",
    };
  }

  const remainingMs = Math.max(0, end - now);
  const totalSeconds = Math.floor(remainingMs / 1000);
  const days = Math.floor(totalSeconds / 86400);
  const hours = Math.floor((totalSeconds % 86400) / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const seconds = totalSeconds % 60;

  const created = new Date(createdAt || now).getTime();
  const totalWindow = Math.max(1, end - created);
  const elapsed = Math.max(0, now - created);
  const percent = Math.min(100, Math.max(0, (elapsed / totalWindow) * 100));

  if (status !== "active" || remainingMs <= 0) {
    return {
      label: "Торги завершены",
      percent: 100,
      isFinished: true,
    };
  }

  return {
    label: `${days}д ${hours}ч ${minutes}м ${seconds}с`,
    percent,
    isFinished: false,
  };
};

function ProductPage({
  selectedAuction,
  bidError,
  successMessage,
  bidUser,
  setBidUser,
  bidAmount,
  setBidAmount,
  handlePlaceBid,
  bidLoading,
  userValue,
  setUserValue,
  handleRecommendBid,
  recommendationLoading,
  recommendationError,
  bidRecommendation,
  offerAmount,
  setOfferAmount,
  handleMakeOffer,
  offerLoading,
  offerError,
  offerResult,
  handleOfferDecision,
  onBack,
}) {
  const images = useMemo(() => {
    if (!selectedAuction) return [];

    if (selectedAuction.image_urls && selectedAuction.image_urls.length) {
      return selectedAuction.image_urls;
    }

    if (selectedAuction.image_url) {
      return [selectedAuction.image_url];
    }

    return [];
  }, [selectedAuction]);

  const [selectedImage, setSelectedImage] = useState(null);
  const [now, setNow] = useState(0);

  useEffect(() => {
    const initialTick = window.setTimeout(() => setNow(Date.now()), 0);
    const interval = window.setInterval(() => setNow(Date.now()), 1000);
    return () => {
      window.clearTimeout(initialTick);
      window.clearInterval(interval);
    };
  }, []);

  if (!selectedAuction) {
    return <div className="empty-box">Товар не выбран</div>;
  }

  const visibleImage =
    selectedImage && images.includes(selectedImage)
      ? selectedImage
      : images[0] || null;

  const analysis = selectedAuction.analysis || {};
  const formulaExplanation = analysis.formula_explanation || {};
  const minBid =
    Number(selectedAuction.current_price || 0) +
    Number(selectedAuction.recommended_bid_step || 0);

  const scoreRows = [
    ["Q_b", "Бренд", analysis.brand_score],
    ["Q_c", "Состояние", analysis.condition_score],
    ["Q_v", "Винтажность", analysis.vintage_score],
    ["Q_r", "Редкость", analysis.rarity_score],
    ["Q", "Ценность", analysis.confirmed_value_score],
    ["A", "Привлекательность", analysis.auction_attractiveness],
  ];

  const formulaRows = [
    ["P_start", formulaExplanation.start_price],
    ["Step", formulaExplanation.bid_step],
    ["E[P_final]", formulaExplanation.expected_final_price],
  ].filter(([, formula]) => Boolean(formula));
  const timer = getRemainingTime(
    selectedAuction.end_time,
    selectedAuction.created_at,
    now,
    selectedAuction.status
  );
  const auctionActive = selectedAuction.status === "active" && !timer.isFinished;
  const bids = selectedAuction.bids || [];
  const offers = selectedAuction.offers || [];
  const pendingOffers = offers.filter((offer) => offer.status === "pending");
  const currentPrice = Number(selectedAuction.current_price || 0);
  const basePrice = Number(analysis.base_price || selectedAuction.start_price || 0);
  const expectedPrice = Number(
    analysis.expected_final_price ||
      selectedAuction.expected_final_price ||
      selectedAuction.current_price ||
      0
  );
  const startPrice = Number(selectedAuction.start_price || 0);
  const bidSeries = [
    {
      label: "Старт",
      amount: startPrice,
      created_at: selectedAuction.created_at,
    },
    ...bids.map((bid) => ({
      label: bid.user,
      amount: Number(bid.amount || 0),
      created_at: bid.created_at,
    })),
  ];
  const tradeEvents = [
    { kind: "start", label: "Старт", amount: startPrice, created_at: selectedAuction.created_at },
    ...bids.map((bid) => ({
      kind: "bid",
      label: bid.user,
      amount: Number(bid.amount || 0),
      created_at: bid.created_at,
    })),
    ...offers.map((offer) => ({
      kind: "offer",
      label: offer.user,
      amount: Number(offer.amount || 0),
      status: offer.status,
      recommendation: offer.recommendation,
      created_at: offer.created_at,
    })),
  ].sort((left, right) => new Date(left.created_at || 0) - new Date(right.created_at || 0));
  const allChartValues = [
    startPrice,
    currentPrice,
    basePrice,
    expectedPrice,
    ...bids.map((bid) => Number(bid.amount || 0)),
    ...offers.map((offer) => Number(offer.amount || 0)),
    ...offers.map((offer) => Number(offer.seller_wait_utility || 0)),
  ].filter((value) => Number.isFinite(value) && value > 0);
  const chartValues = allChartValues.length ? allChartValues : [1];
  const minChartPrice = Math.min(...chartValues) * 0.96;
  const maxChartPrice = Math.max(...chartValues) * 1.04;
  const priceSpread = Math.max(1, maxChartPrice - minChartPrice);
  const yForPrice = (amount) => 50 - ((amount - minChartPrice) / priceSpread) * 42;
  const xForIndex = (index, total) => (total === 1 ? 50 : 8 + (index / (total - 1)) * 84);
  const bidSvgPoints = bidSeries.map((point, index) => {
    const x = xForIndex(index, bidSeries.length);
    const y = yForPrice(point.amount);
    return {
      ...point,
      x,
      y,
    };
  });
  const tradeSvgPoints = tradeEvents.map((point, index) => ({
    ...point,
    x: xForIndex(index, tradeEvents.length),
    y: yForPrice(point.amount),
  }));
  const priceLine = bidSvgPoints.map((point) => `${point.x},${point.y}`).join(" ");
  const guideLines = [
    { label: "P_base", amount: basePrice, className: "base" },
    { label: "E[P_final]", amount: expectedPrice, className: "expected" },
    { label: "Текущая", amount: currentPrice, className: "current" },
  ];
  const insight = getTradeInsight(
    currentPrice,
    basePrice,
    expectedPrice,
    bids.length,
    pendingOffers.length
  );
  const recommendedBidValue = bidRecommendation?.recommended_bid?.recommended_bid;

  return (
    <>
      <section className="hero-banner">
        <div className="product-page-header">
          <button className="secondary-btn" onClick={onBack}>
            ← Назад в каталог
          </button>
          <div>
            <p className="hero-label">Карточка товара</p>
            <h2>{selectedAuction.title}</h2>
            <p>{selectedAuction.brand}</p>
          </div>
        </div>
      </section>

      <div className="product-layout">
        <section className="product-gallery-card">
          <div className="product-main-image">
            {visibleImage ? (
              <img
                src={visibleImage}
                alt={selectedAuction.title}
                className="product-main-img"
              />
            ) : (
              "Фото товара"
            )}
          </div>

          <div className="product-thumbs">
            {images.map((img, index) => (
              <button
                type="button"
                key={index}
                className={`product-thumb ${visibleImage === img ? "active" : ""}`}
                onClick={() => setSelectedImage(img)}
              >
                <img src={img} alt={`thumb-${index}`} className="product-thumb-img" />
              </button>
            ))}
          </div>
        </section>

        <section className="product-info-panel">
          <div className={`auction-timer-card ${timer.isFinished ? "finished" : ""}`}>
            <div>
              <span>До окончания торгов</span>
              <strong>{timer.label}</strong>
            </div>
            <div className="timer-track">
              <div style={{ width: `${timer.percent}%` }} />
            </div>
          </div>

          <div className="auction-price-box large">
            <span>Текущая цена</span>
            <strong>{formatMoney(selectedAuction.current_price)}</strong>
          </div>

          <div className="auction-stats-grid product-stats">
            <div className="stat-box">
              <span>Шаг ставки</span>
              <strong>{formatMoney(selectedAuction.recommended_bid_step)}</strong>
            </div>
            <div className="stat-box">
              <span>Статус</span>
              <strong>
                {selectedAuction.status === "active" ? "Идут торги" : "Завершён"}
              </strong>
            </div>
            <div className="stat-box">
              <span>Количество ставок</span>
              <strong>{selectedAuction.bids?.length || 0}</strong>
            </div>
            <div className="stat-box">
              <span>Минимальная ставка</span>
              <strong>{formatMoney(minBid)}</strong>
            </div>
            <div className="stat-box">
              <span>Прогноз финала</span>
              <strong>{formatMoney(selectedAuction.expected_final_price)}</strong>
            </div>
            <div className="stat-box">
              <span>Окончание</span>
              <strong>{formatDateTime(selectedAuction.end_time)}</strong>
            </div>
          </div>

          <div className="bid-form-card">
            <h3>Сделать ставку</h3>

            {bidError && <div className="error-box">{bidError}</div>}
            {successMessage && <div className="success-box">{successMessage}</div>}

            <form onSubmit={handlePlaceBid}>
              <div className="field">
                <label>Имя пользователя</label>
                <input
                  value={bidUser}
                  onChange={(e) => setBidUser(e.target.value)}
                />
              </div>

              <div className="field">
                <label>Сумма ставки</label>
                <input
                  type="number"
                  step="0.01"
                  value={bidAmount}
                  onChange={(e) => setBidAmount(e.target.value)}
                />
              </div>

              <button
                type="submit"
                className="primary-btn full"
                disabled={bidLoading || !auctionActive}
              >
                {bidLoading
                  ? "Отправляем ставку..."
                  : auctionActive
                  ? "Подтвердить ставку"
                  : "Торги завершены"}
              </button>
            </form>
          </div>

          <div className="bid-form-card buyer-helper-card">
            <h3>Рекомендованная ставка</h3>
            <p className="helper-text">
              Введи максимум, который товар стоит лично для тебя. Модель перебирает
              возможные ставки и выбирает ту, где полезность выигрыша максимальна.
            </p>

            {recommendationError && <div className="error-box">{recommendationError}</div>}

            <form onSubmit={handleRecommendBid}>
              <div className="field">
                <label>Моя максимальная ценность товара</label>
                <input
                  type="number"
                  step="0.01"
                  value={userValue}
                  onChange={(e) => setUserValue(e.target.value)}
                />
              </div>

              <button
                type="submit"
                className="secondary-btn full"
                disabled={recommendationLoading || !auctionActive}
              >
                {recommendationLoading
                  ? "Считаем..."
                  : auctionActive
                  ? "Рассчитать ставку"
                  : "Торги завершены"}
              </button>
            </form>

            {bidRecommendation && (
              <div className="recommendation-result">
                <div>
                  <span>s*</span>
                  <strong>
                    {recommendedBidValue
                      ? formatMoney(recommendedBidValue)
                      : "Ставка невыгодна"}
                  </strong>
                </div>
                <div>
                  <span>P_win</span>
                  <strong>
                    {formatScore(bidRecommendation.recommended_bid?.win_probability)}
                  </strong>
                </div>
                <div>
                  <span>U(s)</span>
                  <strong>{formatMoney(bidRecommendation.recommended_bid?.utility)}</strong>
                </div>

                <p className="recommendation-explain">
                  s* — рекомендуемая ставка, P_win — оценка вероятности выигрыша,
                  U(s) — польза ставки с учётом твоего максимума.
                </p>

                {recommendedBidValue && (
                  <button
                    type="button"
                    className="secondary-btn full"
                    onClick={() => setBidAmount(Number(recommendedBidValue).toFixed(2))}
                  >
                    Подставить в форму ставки
                  </button>
                )}
              </div>
            )}
          </div>

          <div className="bid-form-card offer-card">
            <h3>Досрочный оффер</h3>

            {offerError && <div className="error-box">{offerError}</div>}
            {offerResult && (
              <div className={`offer-result ${offerResult.decision || offerResult.offer?.status}`}>
                <strong>
                  {getDecisionLabel(offerResult.decision || offerResult.offer?.status)}
                </strong>
                <p>
                  {getRecommendationLabel(
                    offerResult.recommendation || offerResult.offer?.recommendation
                  )}
                </p>
                <p>
                  Порог ожидания продавца:{" "}
                  {formatMoney(
                    offerResult.seller_wait_utility ||
                      offerResult.offer?.seller_wait_utility
                  )}
                </p>
                {offerResult.offer?.counter_amount && (
                  <p>Контроффер модели: {formatMoney(offerResult.offer.counter_amount)}</p>
                )}
              </div>
            )}

            <form onSubmit={handleMakeOffer}>
              <div className="field">
                <label>Сумма оффера</label>
                <input
                  type="number"
                  step="0.01"
                  value={offerAmount}
                  onChange={(e) => setOfferAmount(e.target.value)}
                />
              </div>

              <button
                type="submit"
                className="primary-btn full"
                disabled={offerLoading || !auctionActive}
              >
                {offerLoading
                  ? "Отправляем..."
                  : auctionActive
                  ? "Предложить цену сейчас"
                  : "Торги завершены"}
              </button>
            </form>
          </div>

          <div className="bid-form-card seller-offers-card">
            <h3>Панель продавца</h3>
            <p className="helper-text">
              Пока личный кабинет не вынесен отдельно, входящие офферы показаны
              здесь: модель только советует действие, а финальное решение остаётся
              за продавцом.
            </p>

            {!offers.length && (
              <div className="empty-box">Входящих офферов пока нет</div>
            )}

            <div className="seller-offers-list">
              {offers
                .slice()
                .reverse()
                .map((offer) => (
                  <div className="seller-offer-item" key={offer.id}>
                    <div>
                      <strong>{formatMoney(offer.amount)}</strong>
                      <p>
                        {offer.user} · {getDecisionLabel(offer.status)}
                      </p>
                      <p>{getRecommendationLabel(offer.recommendation)}</p>
                      {offer.counter_amount && (
                        <p>Контроффер: {formatMoney(offer.counter_amount)}</p>
                      )}
                    </div>

                    {offer.status === "pending" && (
                      <div className="seller-offer-actions">
                        <button
                          type="button"
                          className="secondary-btn"
                          onClick={() =>
                            handleOfferDecision(selectedAuction.id, offer.id, "reject")
                          }
                        >
                          Отклонить
                        </button>
                        <button
                          type="button"
                          className="secondary-btn"
                          onClick={() =>
                            handleOfferDecision(
                              selectedAuction.id,
                              offer.id,
                              "counteroffer",
                              offer.counter_amount
                            )
                          }
                        >
                          Контроффер
                        </button>
                        <button
                          type="button"
                          className="primary-btn"
                          onClick={() =>
                            handleOfferDecision(selectedAuction.id, offer.id, "accept")
                          }
                        >
                          Принять
                        </button>
                      </div>
                    )}
                  </div>
                ))}
            </div>
          </div>
        </section>
      </div>

      <section className="math-model-section">
        <div className="panel-header">
          <h3>Математическая модель цены</h3>
        </div>

        <div className="math-summary-grid">
          <div className="stat-box">
            <span>Базовая цена P_base</span>
            <strong>{formatMoney(analysis.base_price)}</strong>
          </div>
          <div className="stat-box">
            <span>Старт P_start</span>
            <strong>{formatMoney(selectedAuction.start_price)}</strong>
          </div>
          <div className="stat-box">
            <span>Ожидаемая финальная цена</span>
            <strong>{formatMoney(analysis.expected_final_price)}</strong>
          </div>
        </div>

        <div className="score-grid product-score-grid">
          {scoreRows.map(([code, label, value]) => (
            <div className="score-card" key={code}>
              <span>{code}</span>
              <strong>{formatScore(value)}</strong>
              <p>{label}</p>
            </div>
          ))}
        </div>

        <div className="formula-list compact">
          {formulaRows.map(([code, formula]) => (
            <div className="formula-row" key={code}>
              <span>{code}</span>
              <p>{formula}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="price-dynamics-section">
        <div className="panel-header">
          <h3>Карта торгов</h3>
          <span className="chart-caption">
            {bids.length} ставок · {offers.length} офферов
          </span>
        </div>

        <div className="trade-insight-grid">
          <div className="trade-insight-card buyer">
            <span>Покупателю</span>
            <p>{insight.buyer}</p>
          </div>
          <div className="trade-insight-card seller">
            <span>Продавцу</span>
            <p>{insight.seller}</p>
          </div>
        </div>

        <div className="trade-map">
          <svg viewBox="0 0 100 56" preserveAspectRatio="none" aria-hidden="true">
            <rect className="zone-bargain" x="0" y={yForPrice(basePrice)} width="100" height={56 - yForPrice(basePrice)} />
            <rect
              className="zone-fair"
              x="0"
              y={yForPrice(expectedPrice)}
              width="100"
              height={Math.max(1, yForPrice(basePrice) - yForPrice(expectedPrice))}
            />
            <rect className="zone-hot" x="0" y="0" width="100" height={yForPrice(expectedPrice)} />

            {guideLines.map((line) => (
              <g className={`guide-line ${line.className}`} key={line.label}>
                <line x1="0" x2="100" y1={yForPrice(line.amount)} y2={yForPrice(line.amount)} />
              </g>
            ))}

            <polyline className="bid-line" points={priceLine} />

            {tradeSvgPoints.map((point, index) => (
              <g
                className={`trade-point ${point.kind} ${point.status || ""}`}
                key={`${point.kind}-${point.label}-${index}`}
              >
                <circle cx={point.x} cy={point.y} r={point.kind === "offer" ? "2.3" : "2"} />
              </g>
            ))}
          </svg>

          <div className="trade-map-labels">
            {guideLines.map((line) => (
              <div className={`trade-map-label ${line.className}`} key={line.label}>
                <span>{line.label}</span>
                <strong>{formatMoney(line.amount)}</strong>
              </div>
            ))}
          </div>
        </div>

        <div className="trade-legend">
          <span><i className="legend-dot bid" /> ставка</span>
          <span><i className="legend-dot offer" /> оффер</span>
          <span><i className="legend-line" /> ход текущей цены</span>
        </div>

        <div className="chart-points-list">
          {tradeEvents.map((point, index) => (
            <div className={`chart-point-row ${point.kind}`} key={`${point.label}-${index}`}>
              <span>{point.label}</span>
              <strong>{formatMoney(point.amount)}</strong>
              <p>
                {point.kind === "offer"
                  ? `${getDecisionLabel(point.status)} · ${getRecommendationLabel(point.recommendation)}`
                  : formatDateTime(point.created_at)}
              </p>
            </div>
          ))}
        </div>
      </section>

      <section className="bids-history-card">
        <h3>История ставок</h3>

        <div className="bids-list">
          {(selectedAuction.bids || [])
            .slice()
            .reverse()
            .map((bid, index) => (
              <div className="bid-item" key={index}>
                <div>
                  <strong>{bid.user}</strong>
                  <p>{formatDateTime(bid.created_at)}</p>
                </div>
                <span>{formatMoney(bid.amount)}</span>
              </div>
            ))}
        </div>
      </section>
    </>
  );
}

export default ProductPage;
