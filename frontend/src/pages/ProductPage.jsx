import { useEffect, useMemo, useState } from "react";

const toFiniteNumber = (value) => {
  const number = Number(value);
  return Number.isFinite(number) ? number : null;
};

const formatMoney = (value) => {
  const number = toFiniteNumber(value);
  return number === null ? "-" : `${Math.round(number).toLocaleString("ru-RU")} ₽`;
};

const formatScore = (value) => {
  const number = toFiniteNumber(value);
  return number === null ? "-" : number.toFixed(2);
};

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

const ATTRIBUTE_LABELS = {
  brand: "Бренд",
  category: "Категория",
  subcategory: "Тип вещи",
  condition: "Состояние",
  size: "Размер",
  material: "Материал",
  colors: "Цвет",
  color: "Цвет",
  style: "Стиль",
  estimated_age: "Возраст",
  has_tag: "Бирка",
  defects: "Дефекты",
  seller_comment: "Комментарий продавца",
};

const ATTRIBUTE_VALUES = {
  category: {
    outerwear: "Верхняя одежда",
    tops: "Верх",
    bottoms: "Низ",
    shoes: "Обувь",
    accessories: "Аксессуары",
  },
  subcategory: {
    bomber: "Бомбер",
    leather_jacket: "Кожаная куртка",
    denim_jacket: "Джинсовая куртка",
    windbreaker: "Ветровка",
    puffer: "Пуховик",
    sheepskin: "Дублёнка",
    coat: "Пальто",
    trench: "Тренч",
    hoodie: "Худи / свитшот",
    tshirt: "Футболка",
    shirt: "Рубашка / лонгслив",
    sweater: "Свитер",
    longsleeve: "Лонгслив",
    jeans: "Джинсы",
    pants: "Брюки",
    shorts: "Шорты",
    skirt: "Юбка",
    sneakers: "Кроссовки",
    boots: "Ботинки",
    loafers: "Лоферы",
    bag: "Сумка",
    cap: "Кепка",
    belt: "Ремень",
    scarf: "Шарф",
  },
  condition: {
    excellent: "Отличное",
    good: "Хорошее",
    normal: "Нормальное",
    bad: "С дефектами",
  },
};

const formatAttributeValue = (key, value) => {
  if (value === undefined || value === null || value === "") return null;
  if (Array.isArray(value)) {
    const cleanValues = value.map((item) => String(item).trim()).filter(Boolean);
    return cleanValues.length ? cleanValues.join(", ") : null;
  }
  if (typeof value === "string" && value.trim().toLowerCase() === "unknown") return null;
  if (key === "has_tag") return value ? "Есть" : "Нет";
  if (key === "estimated_age") {
    const age = Number(value);
    if (!Number.isFinite(age) || age <= 0) return null;
    return `${age} лет`;
  }
  return ATTRIBUTE_VALUES[key]?.[value] || String(value);
};

const buildCharacteristicRows = (auction) => {
  const questionnaire = auction?.questionnaire || {};
  const merged = {
    brand: auction?.brand || questionnaire.brand,
    ...questionnaire,
  };
  const orderedKeys = [
    "brand",
    "category",
    "subcategory",
    "condition",
    "size",
    "material",
    "colors",
    "color",
    "style",
    "estimated_age",
    "has_tag",
    "defects",
    "seller_comment",
  ];

  return orderedKeys
    .map((key) => ({
      key,
      label: ATTRIBUTE_LABELS[key],
      value: formatAttributeValue(key, merged[key]),
    }))
    .filter((row) => row.label && row.value);
};

const getDecisionLabel = (decision) => {
  const labels = {
    accepted: "Оффер принят",
    counteroffer: "Продавец предложил встречную цену",
    rejected: "Оффер отклонён",
    pending: "Ожидает решения продавца",
  };
  return labels[decision] || "Оффер обработан";
};

const getRecommendationLabel = (recommendation) => {
  const labels = {
    accept: "модель советует принять",
    counteroffer: "модель советует предложить встречную цену",
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

function PricingExplanation({ analysis }) {
  const hasAnalysis =
    analysis && Object.keys(analysis).length > 0 && analysis.base_price !== undefined;

  const sourceLabel =
    analysis?.base_price_source === "ml_model" ? "ML модель" : "Резервная формула";

  const sections = [
    {
      title: "Базовая цена",
      items: [
        {
          label: "Базовая цена",
          value: formatMoney(analysis?.base_price),
          hint: "P_base оценивает рыночную стоимость товара до начала торгов.",
        },
        {
          label: "Источник",
          value: sourceLabel,
          hint: "ML модель используется при наличии обученного файла, иначе применяется резервная формула.",
        },
        {
          label: "Доступность модели",
          value: analysis?.model_available ? "Да" : "Нет",
          hint: "Показывает, была ли загружена обученная модель базовой цены.",
        },
      ],
    },
    {
      title: "Характеристики товара",
      items: [
        {
          label: "Бренд",
          value: formatScore(analysis?.brand_score),
          hint: "Коэффициент бренда отражает рыночную ценность бренда.",
        },
        {
          label: "Состояние",
          value: formatScore(analysis?.condition_score),
          hint: "Учитывает сохранность вещи и снижает цену при дефектах.",
        },
        {
          label: "Винтажность",
          value: formatScore(analysis?.vintage_score),
          hint: "Возраст повышает оценку только для брендов, где винтаж имеет рыночный смысл.",
        },
        {
          label: "Редкость",
          value: formatScore(analysis?.rarity_score),
          hint: "Оценивает редкость модели, бирки, лимитированность и архивность.",
        },
      ],
    },
    {
      title: "Рыночные факторы",
      items: [
        {
          label: "Спрос (D)",
          value: formatScore(analysis?.demand_score),
          hint: "D отражает реальные торговые действия: ставки, офферы и рост цены.",
        },
        {
          label: "Интерес (I)",
          value: formatScore(analysis?.interest_score),
          hint: "I отражает интерес без ставки: просмотры, лайки и избранное.",
        },
        {
          label: "Неопределённость (V)",
          value: formatScore(analysis?.uncertainty_score),
          hint: "Показывает разброс возможной цены и влияние редкости товара.",
        },
      ],
    },
    {
      title: "Итоговые коэффициенты",
      items: [
        {
          label: "Подтверждённая ценность (Q)",
          value: formatScore(analysis?.confirmed_value_score),
          hint: "Q объединяет бренд, состояние, редкость и винтажность товара.",
        },
        {
          label: "Потенциал до старта (A_pre)",
          value: formatScore(analysis?.auction_potential_pre),
          hint: "A_pre влияет на стартовую цену и начальный шаг ставки.",
        },
        {
          label: "Активность торгов (A_live)",
          value: formatScore(analysis?.auction_activity_live ?? analysis?.auction_attractiveness),
          hint: "A_live используется после публикации для прогноза финала и решений продавца.",
        },
        {
          label: "Поведение ставок (B)",
          value: formatScore(analysis?.buyer_behavior_score),
          hint: "B учитывает фактическое число ставок, конкуренцию и медианный рост цены по датасету аукционов.",
        },
        {
          label: "Bucket ставок",
          value: analysis?.bids_bucket || analysis?.auction_behavior?.bids_bucket || "0",
          hint: "Диапазон количества ставок из Online Auctions Dataset: 1, 2-3, 4-6, 7-12, 13+.",
        },
      ],
    },
    {
      title: "Результат модели",
      items: [
        {
          label: "Рекомендованная стартовая цена",
          value: formatMoney(analysis?.recommended_start_price),
          hint: "Старт ниже базовой цены стимулирует первые ставки, но ограничен нижним порогом.",
        },
        {
          label: "Рекомендованный шаг ставки",
          value: formatMoney(analysis?.recommended_bid_step),
          hint: "Шаг растёт вместе с привлекательностью и базовой стоимостью лота.",
        },
        {
          label: "Осторожный прогноз",
          value: formatMoney(analysis?.conservative_final_price),
          hint: "Нижний сценарий завершения торгов при слабом развитии активности.",
        },
        {
          label: "Прогноз финальной цены",
          value: formatMoney(analysis?.expected_final_price),
          hint: "Оценка завершения торгов после калибровки по реальному поведению ставок.",
        },
        {
          label: "Оптимистичный прогноз",
          value: formatMoney(analysis?.optimistic_final_price),
          hint: "Верхний сценарий при переходе лота в более активный bucket ставок.",
        },
        {
          label: "Auction uplift",
          value: formatScore(analysis?.auction_uplift || analysis?.auction_behavior?.auction_uplift),
          hint: "Перенесённая на fashion resale часть медианного final/start роста из Online Auctions Dataset.",
        },
      ],
    },
  ];

  return (
    <section className="pricing-explanation-section">
      <div className="panel-header">
        <h3>Как рассчитана цена</h3>
      </div>

      {!hasAnalysis ? (
        <div className="empty-box pricing-unavailable">Данные анализа недоступны</div>
      ) : (
        <>
          <div className="pricing-explanation-grid">
            {sections.map((section) => (
              <div className="pricing-explanation-group" key={section.title}>
                <h4>{section.title}</h4>

                {section.items.map((item) => (
                  <div className="pricing-explanation-item" key={item.label}>
                    <span>{item.label}</span>
                    <strong>{item.value}</strong>
                    <p>{item.hint}</p>
                  </div>
                ))}
              </div>
            ))}
          </div>

          <p className="pricing-explanation-note">
            Прогноз сформирован на основе ML resale price model, auction behavior
            analysis и активности пользователей. Mercari отвечает за P_base, а
            Online Auctions Dataset отвечает только за поведение торгов.
          </p>
        </>
      )}
    </section>
  );
}

function ProductPage({
  selectedAuction,
  bidError,
  successMessage,
  bidUser,
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
  handleLotSignal,
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
  const [imageViewerOpen, setImageViewerOpen] = useState(false);
  const [analysisOpen, setAnalysisOpen] = useState(false);

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
  const visibleImageIndex = visibleImage ? images.indexOf(visibleImage) : -1;
  const changeImage = (direction) => {
    if (!images.length) return;
    const currentIndex = visibleImageIndex >= 0 ? visibleImageIndex : 0;
    const nextIndex = (currentIndex + direction + images.length) % images.length;
    setSelectedImage(images[nextIndex]);
  };

  const analysis = selectedAuction.is_owner
    ? selectedAuction.analysis || selectedAuction.pricing_result || {}
    : {};
  const hasPrivateAnalysis = Boolean(selectedAuction.is_owner && analysis?.base_price);
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
    ["A_pre", "Потенциал до старта", analysis.auction_potential_pre],
    ["A_live", "Активность торгов", analysis.auction_activity_live ?? analysis.auction_attractiveness],
  ];

  const formulaRows = [
    ["P_start", formulaExplanation.start_price],
    ["Step", formulaExplanation.bid_step],
    ["A_pre", formulaExplanation.auction_potential_pre],
    ["A_live", formulaExplanation.auction_activity_live || formulaExplanation.auction_attractiveness],
    ["B_bid", formulaExplanation.auction_behavior],
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
  const initialExpectedPrice = Number(
    analysis.initial_expected_final_price ||
      selectedAuction.initial_expected_final_price ||
      expectedPrice
  );
  const chartExpectedPrice = initialExpectedPrice || expectedPrice;
  const overInitialForecast =
    hasPrivateAnalysis && chartExpectedPrice > 0 && currentPrice > chartExpectedPrice * 1.05;
  const forecastRatio = chartExpectedPrice > 0 ? currentPrice / chartExpectedPrice : 0;
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
    chartExpectedPrice,
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
    ...(hasPrivateAnalysis
      ? [
          { label: "P_base", amount: basePrice, className: "base" },
          { label: "Исходный прогноз", amount: chartExpectedPrice, className: "expected" },
        ]
      : [{ label: "Старт", amount: startPrice, className: "base" }]),
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
  const characteristicRows = buildCharacteristicRows(selectedAuction);

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
          <div className="product-media-row">
            <div className="product-main-image">
              {visibleImage ? (
                <button
                  className="product-image-open"
                  type="button"
                  onClick={() => setImageViewerOpen(true)}
                >
                  <img
                    src={visibleImage}
                    alt={selectedAuction.title}
                    className="product-main-img"
                  />
                </button>
              ) : (
                <div className="product-image-placeholder">Фото товара</div>
              )}
              {images.length > 1 && (
                <div className="product-gallery-controls">
                  <button type="button" onClick={() => changeImage(-1)}>‹</button>
                  <span>{visibleImageIndex + 1} / {images.length}</span>
                  <button type="button" onClick={() => changeImage(1)}>›</button>
                </div>
              )}
            </div>

            <div className="lot-signal-actions product-side-signals">
              <button
                type="button"
                className={`secondary-btn product-signal-button like-signal ${
                  selectedAuction.viewer_signals?.liked ? "active-signal" : ""
                }`}
                aria-pressed={Boolean(selectedAuction.viewer_signals?.liked)}
                onClick={() => handleLotSignal?.("like")}
              >
                <span>{selectedAuction.viewer_signals?.liked ? "Понравилось" : "Нравится"}</span>
                <strong>{selectedAuction.likes_count || 0}</strong>
              </button>
              <button
                type="button"
                className={`secondary-btn product-signal-button favorite-signal ${
                  selectedAuction.viewer_signals?.favorited ? "active-signal" : ""
                }`}
                aria-pressed={Boolean(selectedAuction.viewer_signals?.favorited)}
                onClick={() => handleLotSignal?.("favorite")}
              >
                <span>
                  {selectedAuction.viewer_signals?.favorited
                    ? "В избранном"
                    : "Добавить в избранное"}
                </span>
                <strong>{selectedAuction.favorites_count || 0}</strong>
              </button>
              <div className="signal-static">
                <span>Просмотры</span>
                <strong>{selectedAuction.views_count || 0}</strong>
              </div>
            </div>
          </div>

          <section className="product-characteristics-card">
            <div className="panel-header">
              <h3>Характеристики</h3>
            </div>
            {characteristicRows.length ? (
              <div className="characteristics-grid">
                {characteristicRows.map((row) => (
                  <div className="characteristic-row" key={row.key}>
                    <span>{row.label}</span>
                    <strong>{row.value}</strong>
                  </div>
                ))}
              </div>
            ) : (
              <div className="empty-box compact">Продавец не заполнил характеристики</div>
            )}
          </section>
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
            {hasPrivateAnalysis ? (
              <div className="stat-box">
                <span>Прогноз финала</span>
                <strong>
                  {formatMoney(analysis.expected_final_price || selectedAuction.expected_final_price)}
                </strong>
              </div>
            ) : (
              <div className="stat-box">
                <span>Стартовая цена</span>
                <strong>{formatMoney(selectedAuction.start_price)}</strong>
              </div>
            )}
            <div className="stat-box">
              <span>Окончание</span>
              <strong>{formatDateTime(selectedAuction.end_time)}</strong>
            </div>
          </div>

          {selectedAuction.status === "finished" && selectedAuction.final_summary && (
            <div className="auction-final-card">
              <span>Итог торгов</span>
              <strong>{formatMoney(selectedAuction.final_summary.final_price)}</strong>
              <p>
                Победитель: {selectedAuction.final_summary.winner || "не определён"}
              </p>
              <p>
                Продавец:{" "}
                {selectedAuction.seller_public_profile?.revealed
                  ? selectedAuction.seller_public_profile.display_name
                  : "скрыт настройками профиля"}
              </p>
            </div>
          )}

          {hasPrivateAnalysis && (
            <button
              className="analysis-open-btn"
              type="button"
              onClick={() => setAnalysisOpen(true)}
            >
              Открыть математический анализ лота
            </button>
          )}

          <div className="bid-form-card">
            <h3>Сделать ставку</h3>

            {bidError && <div className="error-box">{bidError}</div>}
            {successMessage && <div className="success-box">{successMessage}</div>}

            <form onSubmit={handlePlaceBid}>
              <div className="field">
                <label>Покупатель</label>
                <input
                  value={bidUser}
                  readOnly
                  placeholder="Войдите в аккаунт"
                />
              </div>

              <div className="field">
                <label>Сумма ставки</label>
                <input
                  type="number"
                  step="1"
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
                  step="1"
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
                  <span>Ставка</span>
                  <strong>
                    {recommendedBidValue
                      ? formatMoney(recommendedBidValue)
                      : "Ставка невыгодна"}
                  </strong>
                </div>
                <div>
                  <span>Шанс</span>
                  <strong>
                    {formatScore(bidRecommendation.recommended_bid?.win_probability)}
                  </strong>
                </div>
                <div>
                  <span>Выгода</span>
                  <strong>{formatMoney(bidRecommendation.recommended_bid?.utility)}</strong>
                </div>

                <p className="recommendation-explain buyer-only-note">
                  s* — рекомендуемая ставка, P_win — оценка вероятности выигрыша,
                  U(s) — польза ставки с учётом твоего максимума.
                </p>

                {recommendedBidValue && (
                  <button
                    type="button"
                    className="secondary-btn full"
                    onClick={() => setBidAmount(String(Math.round(Number(recommendedBidValue))))}
                  >
                    Подставить в форму ставки
                  </button>
                )}
              </div>
            )}
          </div>

          <div className="bid-form-card offer-card">
            <h3>Предложить цену продавцу</h3>
            <p className="helper-text">
              Оффер — предложение купить лот досрочно. Продавец увидит его в кабинете
              и сможет принять, отклонить или отправить встречную цену.
            </p>

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
                {offerResult.offer?.counter_amount && (
                  <p>Встречная цена продавца: {formatMoney(offerResult.offer.counter_amount)}</p>
                )}
              </div>
            )}

            <form onSubmit={handleMakeOffer}>
              <div className="field">
                <label>Сумма оффера</label>
                <input
                  type="number"
                  step="1"
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

        </section>
      </div>

      {analysisOpen && hasPrivateAnalysis && (
        <div className="seller-modal-backdrop analysis-modal-backdrop" role="dialog" aria-modal="true">
          <div className="analysis-modal-card">
            <div className="seller-modal-header">
              <h3>Математический анализ лота</h3>
              <button className="secondary-btn" type="button" onClick={() => setAnalysisOpen(false)}>
                Закрыть
              </button>
            </div>
            <PricingExplanation analysis={analysis} />

      <section className="math-model-section analysis-modal-section">
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
          </div>
        </div>
      )}

      <section className="price-dynamics-section">
        <div className="panel-header">
          <h3>Карта торгов</h3>
          <span className="chart-caption">
            {bids.length} ставок
          </span>
        </div>

        <div className="trade-insight-grid">
          <div className="trade-insight-card buyer">
            <span>Покупателю</span>
            <p>{insight.buyer}</p>
          </div>
          {hasPrivateAnalysis && (
            <div className="trade-insight-card seller">
              <span>Продавцу</span>
              <p>{insight.seller}</p>
            </div>
          )}
        </div>

        {overInitialForecast && (
          <div className="forecast-break-card">
            <strong>Прогноз перебит</strong>
            <p>
              Текущая цена выше исходного прогноза модели в {forecastRatio.toFixed(1)} раза.
              На графике это показано отдельной линией «Исходный прогноз», чтобы рост не
              прятался за автоматическим масштабом.
            </p>
          </div>
        )}

        <div className="trade-map">
          <svg viewBox="0 0 100 56" preserveAspectRatio="xMidYMid meet" aria-hidden="true">
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
                <circle cx={point.x} cy={point.y} r={point.kind === "offer" ? "1.8" : "1.7"} />
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

      {imageViewerOpen && visibleImage && (
        <div className="image-lightbox" role="dialog" aria-modal="true">
          <button className="image-lightbox-close" type="button" onClick={() => setImageViewerOpen(false)}>
            Закрыть
          </button>
          <img src={visibleImage} alt={selectedAuction.title} />
        </div>
      )}
    </>
  );
}

export default ProductPage;
