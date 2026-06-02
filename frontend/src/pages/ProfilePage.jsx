import { useEffect, useState } from "react";

const formatMoney = (value) => {
  const number = Number(value);
  return Number.isFinite(number) ? `${Math.round(number).toLocaleString("ru-RU")} ₽` : "—";
};

const toDateTimeLocalValue = (value) => {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  const timezoneOffset = date.getTimezoneOffset() * 60000;
  return new Date(date.getTime() - timezoneOffset).toISOString().slice(0, 16);
};

const statusLabel = (status) => {
  const labels = {
    active: "Активен",
    finished: "Завершён",
    pending: "Ждёт ответа продавца",
    accepted: "Принят",
    rejected: "Отклонён",
    counteroffer: "Встречная цена отправлена покупателю",
  };
  return labels[status] || status || "—";
};

const recommendationLabel = (recommendation) => {
  const labels = {
    accept: "модель советует принять",
    reject: "модель советует отклонить",
    counteroffer: "модель советует предложить встречную цену",
  };
  return labels[recommendation] || "нет рекомендации";
};

const offerRoleText = {
  buyer:
    "Оффер отправляет покупатель. Пока статус «ждёт ответа», он находится у продавца во входящих офферах. Если продавец отправит встречную цену, она появится здесь, в твоих офферах.",
  seller:
    "Во входящих офферах показаны только предложения покупателей, которые ждут твоего решения. Встречная цена — это твой ответ покупателю, а не действие модели.",
};

const offerStageLabel = (offer, role = "buyer") => {
  if (offer.status === "pending") {
    return role === "seller" ? "Новый оффер покупателя" : "Ждёт решения продавца";
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

function OfferFlowHint({ role }) {
  return (
    <div className="offer-flow-hint">
      <strong>{role === "seller" ? "Как продавец работает с оффером" : "Как покупатель видит оффер"}</strong>
      <p>{offerRoleText[role]}</p>
      <div className="offer-flow-steps">
        <span>1. покупатель отправляет цену</span>
        <span>2. продавец принимает, отклоняет или предлагает встречную</span>
        <span>3. покупатель отвечает только на встречную цену</span>
      </div>
    </div>
  );
}

function StatCard({ label, value }) {
  return (
    <div className="profile-stat-card">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

const formatMetric = (value) =>
  typeof value === "number" ? value.toFixed(3) : value ?? "—";

const buyerBidStatus = (item) => {
  const isFinished = item.auction?.status === "finished";

  if (isFinished && item.is_leading) {
    return { className: "good", label: "Вы выиграли торги" };
  }

  if (isFinished) {
    return { className: "muted", label: "Торги завершены" };
  }

  return item.is_leading
    ? { className: "good", label: "Вы лидируете" }
    : { className: "warn", label: "Ставку перебили" };
};

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

function ProfileEditor({ user, profileMessage, handleProfileUpdate }) {
  const [editing, setEditing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState({
    display_name: "",
    email: "",
    phone: "",
    age: "",
    city: "",
    bio: "",
    is_incognito: false,
  });

  useEffect(() => {
    setForm({
      display_name: user?.name || user?.display_name || "",
      email: user?.email || "",
      phone: user?.phone || "",
      age: user?.age || "",
      city: user?.city || "",
      bio: user?.bio || "",
      is_incognito: Boolean(user?.is_incognito),
    });
  }, [user]);

  const updateField = (event) => {
    const { name, value, type, checked } = event.target;
    setForm((prev) => ({
      ...prev,
      [name]: type === "checkbox" ? checked : value,
    }));
  };

  const submitProfile = async (event) => {
    event.preventDefault();
    setSaving(true);
    try {
      await handleProfileUpdate({
        display_name: form.display_name,
        email: form.email,
        phone: form.phone,
        age: form.age ? Number(form.age) : null,
        city: form.city,
        bio: form.bio,
        is_incognito: form.is_incognito,
      });
      setEditing(false);
    } finally {
      setSaving(false);
    }
  };

  if (!editing) {
    return (
      <div className="profile-details-card">
        <div>
          <span>Email</span>
          <strong>{user?.email || "—"}</strong>
        </div>
        <div>
          <span>Телефон</span>
          <strong>{user?.phone || "—"}</strong>
        </div>
        <div>
          <span>Город</span>
          <strong>{user?.city || "—"}</strong>
        </div>
        <div>
          <span>Показ продавца</span>
          <strong>{user?.is_incognito ? "Инкогнито" : "Открыто после торгов"}</strong>
        </div>
        {profileMessage && <div className="success-box compact">{profileMessage}</div>}
        <button className="secondary-btn full" type="button" onClick={() => setEditing(true)}>
          Редактировать профиль
        </button>
      </div>
    );
  }

  return (
    <form className="profile-edit-form" onSubmit={submitProfile}>
      <div className="field">
        <label>Имя в профиле</label>
        <input name="display_name" value={form.display_name} onChange={updateField} />
      </div>
      <div className="field">
        <label>Email</label>
        <input name="email" type="email" value={form.email} onChange={updateField} />
      </div>
      <div className="field">
        <label>Телефон</label>
        <input name="phone" value={form.phone} onChange={updateField} placeholder="+7..." />
      </div>
      <div className="field-row">
        <div className="field">
          <label>Возраст</label>
          <input name="age" type="number" value={form.age} onChange={updateField} />
        </div>
        <div className="field">
          <label>Город</label>
          <input name="city" value={form.city} onChange={updateField} />
        </div>
      </div>
      <div className="field">
        <label>О себе</label>
        <textarea name="bio" value={form.bio} onChange={updateField} />
      </div>
      <label className="checkbox-field profile-incognito-toggle">
        <input
          type="checkbox"
          name="is_incognito"
          checked={form.is_incognito}
          onChange={updateField}
        />
        <span>Не показывать имя продавца после завершения торгов</span>
      </label>
      <div className="profile-edit-actions">
        <button className="secondary-btn" type="button" onClick={() => setEditing(false)}>
          Отмена
        </button>
        <button className="primary-btn" type="submit" disabled={saving}>
          {saving ? "Сохраняем..." : "Сохранить профиль"}
        </button>
      </div>
    </form>
  );
}

function SellerListingCard({
  auction,
  handleSelectAuction,
  handleUpdateAuction,
  handleUploadAuctionImages,
  handleAcceptBid,
}) {
  const [isEditing, setIsEditing] = useState(false);
  const [bidsOpen, setBidsOpen] = useState(false);
  const [analysisOpen, setAnalysisOpen] = useState(false);
  const [actionMessage, setActionMessage] = useState("");
  const [form, setForm] = useState({
    title: auction.title || "",
    description: auction.description || "",
    start_price: auction.start_price || "",
    recommended_bid_step: auction.recommended_bid_step || "",
    end_time: toDateTimeLocalValue(auction.end_time),
  });
  const [saving, setSaving] = useState(false);
  const [imageUploading, setImageUploading] = useState(false);
  const analysis = auction.analysis || {};
  const formulaExplanation = analysis.formula_explanation || {};
  const bids = auction.bids || [];
  const hasBids = bids.length > 0;
  const isActive = auction.status === "active";
  const canEditStartPrice = isActive && !hasBids;
  const canEditAuctionRules = isActive;
  const basePriceSource =
    analysis.base_price_source === "ml_model" ? "ML-модель" : "резервная формула";

  const calculationRows = [
    {
      code: "P_base",
      label: "Базовая цена",
      value: formatMoney(analysis.base_price),
      description: `Оценка рыночной стоимости до торгов. Источник: ${basePriceSource}.`,
    },
    {
      code: "Q_b",
      label: "Бренд",
      value: formatMetric(analysis.brand_score),
      description: "Показывает рыночную силу бренда по справочнику и датасету.",
    },
    {
      code: "Q_c",
      label: "Состояние",
      value: formatMetric(analysis.condition_score),
      description: "Учитывает износ: excellent, good, normal или bad.",
    },
    {
      code: "Q_v",
      label: "Винтажность",
      value: formatMetric(analysis.vintage_score),
      description: "Возраст повышает ценность только у брендов, где винтаж имеет смысл.",
    },
    {
      code: "R",
      label: "Редкость",
      value: formatMetric(analysis.rarity_score),
      description: "Учитывает бирку, возраст, бренд и признаки редкости в описании.",
    },
    {
      code: "D",
      label: "Спрос",
      value: formatMetric(analysis.demand_score),
      description: "Показывает реальные торговые действия: ставки, офферы, скорость и рост цены.",
    },
    {
      code: "I",
      label: "Интерес",
      value: formatMetric(analysis.interest_score),
      description: "Показывает вовлечённость без обязательной ставки: просмотры, лайки и избранное.",
    },
    {
      code: "V",
      label: "Неопределённость",
      value: formatMetric(analysis.uncertainty_score),
      description: "Показывает риск разброса цены и влияние редкости.",
    },
    {
      code: "Q",
      label: "Подтверждённая ценность",
      value: formatMetric(analysis.confirmed_value_score),
      description: "Итоговая ценность товара по бренду, состоянию, редкости и винтажности.",
    },
    {
      code: "A_pre",
      label: "Потенциал до старта",
      value: formatMetric(analysis.auction_potential_pre),
      description: "Предварительный потенциал аукциона по признакам товара. Он влияет на старт и шаг.",
    },
    {
      code: "A_live",
      label: "Активность торгов",
      value: formatMetric(analysis.auction_activity_live ?? analysis.auction_attractiveness),
      description: "Живая активность после публикации: ставки, офферы, интерес и рост цены.",
    },
    {
      code: "P_start",
      label: "Рекомендованный старт",
      value: formatMoney(analysis.recommended_start_price || auction.start_price),
      description: "Стартовая цена ниже базовой, чтобы стимулировать первые ставки.",
    },
    {
      code: "Step",
      label: "Шаг ставки",
      value: formatMoney(analysis.recommended_bid_step || auction.recommended_bid_step),
      description: "Стартовый шаг фиксируется при публикации. Live-шаг ниже показан как рекомендация.",
    },
    {
      code: "Step live",
      label: "Live-шаг",
      value: formatMoney(analysis.live_recommended_bid_step),
      description: "Рекомендованный шаг при текущей активности торгов, без автоматической смены правил лота.",
    },
    {
      code: "P_cons",
      label: "Осторожный прогноз",
      value: formatMoney(analysis.conservative_final_price),
      description: "Нижний сценарий завершения торгов при слабом развитии активности.",
    },
    {
      code: "E[P_final]",
      label: "Прогноз финала",
      value: formatMoney(analysis.expected_final_price || auction.expected_final_price),
      description: "Ожидаемая финальная цена с учетом модели и текущей активности.",
    },
    {
      code: "P_opt",
      label: "Оптимистичный прогноз",
      value: formatMoney(analysis.optimistic_final_price),
      description: "Верхний сценарий, если количество ставок перейдет в более активный bucket.",
    },
    {
      code: "B_bid",
      label: "Bucket ставок",
      value: analysis.bids_bucket || analysis.auction_behavior?.bids_bucket || "0",
      description: `Источник: ${analysis.auction_behavior_source || "Online Auctions Dataset"}. Median final/start: ${analysis.median_final_start_ratio || "-"}.`,
    },
  ];

  const formulaRows = [
    {
      formula: "Q = 0.30Q_b + 0.25Q_c + 0.25R + 0.20Q_v",
      text:
        formulaExplanation.confirmed_value_score ||
        "Q объединяет подтверждаемые признаки товара: бренд, состояние, редкость и винтажность.",
    },
    {
      formula: "A_pre = 0.40Q + 0.22R + 0.14Q_v + 0.14Q_b + 0.10C_a",
      text:
        formulaExplanation.auction_potential_pre ||
        "A_pre считается до публикации и влияет на стартовую цену и начальный шаг ставки.",
    },
    {
      formula: "A_live = 0.38D + 0.22I + 0.15V + 0.20Q + 0.05P_ratio",
      text:
        formulaExplanation.auction_activity_live ||
        "A_live считается после публикации и показывает текущую активность торгов.",
    },
    {
      formula: "P_start = max(P_base * (1 - 0.05 - 0.25A_pre), 0.55P_base)",
      text:
        formulaExplanation.start_price ||
        "Стартовая цена не проваливается ниже разумного порога, но остается ниже базовой.",
    },
    {
      formula: "uplift = 1 + (median(final/start) - 1) * k_fashion",
      text:
        formulaExplanation.auction_behavior ||
        "Online Auctions Dataset используется как источник поведения торгов, а не как источник цен одежды.",
    },
    {
      formula: "E[P_final] = current_price * uplift",
      text:
        formulaExplanation.expected_final_price ||
        "Финальная цена выводится диапазоном: осторожный, ожидаемый и оптимистичный сценарии.",
    },
  ];

  const parseMoneyInput = (value) => {
    const normalized = String(value || "").replace(",", ".");
    const number = Number(normalized);
    return Number.isFinite(number) ? number : undefined;
  };

  const updateField = (event) => {
    const { name, value } = event.target;
    setForm((prev) => ({
      ...prev,
      [name]: value,
    }));
  };

  const submitEdit = async (event) => {
    event.preventDefault();
    setSaving(true);
    try {
      const patch = {
        title: form.title,
        description: form.description,
      };

      if (canEditStartPrice) {
        patch.start_price = parseMoneyInput(form.start_price);
      }

      if (canEditAuctionRules) {
        patch.recommended_bid_step = parseMoneyInput(form.recommended_bid_step);
        patch.end_time = form.end_time ? new Date(form.end_time).toISOString() : null;
      }

      await handleUpdateAuction(auction.id, patch);
      setActionMessage("Изменения по лоту сохранены");
      setIsEditing(false);
    } finally {
      setSaving(false);
    }
  };

  const finishAuction = async () => {
    await handleUpdateAuction(auction.id, { status: "finished" });
    setActionMessage("Торги завершены. Итоговая цена зафиксирована.");
  };

  const acceptBid = async (bidId) => {
    await handleAcceptBid(auction.id, bidId);
    setActionMessage("Ставка принята. Аукцион завершён по выбранной цене.");
    setBidsOpen(false);
  };

  const uploadImages = async (fileList) => {
    if (!fileList?.length) return;
    setImageUploading(true);
    try {
      await handleUploadAuctionImages(auction, fileList);
      setActionMessage("Фото добавлены к лоту");
    } catch (error) {
      setActionMessage(error.message || "Не удалось добавить фото");
    } finally {
      setImageUploading(false);
    }
  };

  const editGallery = [
    ...(Array.isArray(auction.image_urls) ? auction.image_urls : []),
    auction.image_url,
  ].filter(Boolean);
  const uniqueEditGallery = [...new Set(editGallery)];

  return (
    <div className="profile-seller-card seller-management-card">
      <AuctionMiniCard auction={auction} onOpen={handleSelectAuction} />

      <div className="seller-private-grid">
        <div className="profile-row">
          <span>Ставки</span>
          <strong>{bids.length}</strong>
        </div>
        <div className="profile-row">
          <span>Офферы</span>
          <strong>{auction.offers?.length || 0}</strong>
        </div>
        <div className="profile-row">
          <span>Просмотры</span>
          <strong>{auction.views_count || 0}</strong>
        </div>
        <div className="profile-row">
          <span>Прогноз финала</span>
          <strong>{formatMoney(auction.expected_final_price)}</strong>
        </div>
        <div className="profile-row seller-metric-row" title="D показывает фактические торговые действия: ставки, офферы, скорость ставок и рост цены. Просмотры и лайки сюда не входят">
          <span>Спрос D</span>
          <strong>{formatMetric(analysis.demand_score)}</strong>
        </div>
        <div className="profile-row seller-metric-row" title="I показывает интерес до покупки: просмотры, лайки и избранное, но не ставки">
          <span>Интерес I</span>
          <strong>{formatMetric(analysis.interest_score)}</strong>
        </div>
        <div className="profile-row seller-metric-row" title="A_pre используется до публикации для старта и шага ставки">
          <span>Потенциал A_pre</span>
          <strong>{formatMetric(analysis.auction_potential_pre)}</strong>
        </div>
        <div className="profile-row seller-metric-row" title="A_live используется после публикации для прогноза и решений продавца">
          <span>Активность A_live</span>
          <strong>{formatMetric(analysis.auction_activity_live ?? analysis.auction_attractiveness)}</strong>
        </div>
        <div className="profile-row seller-metric-row" title="Q — подтверждённая ценность по бренду, состоянию, редкости и винтажности">
          <span>Ценность Q</span>
          <strong>{formatMetric(analysis.confirmed_value_score)}</strong>
        </div>
      </div>

      <div className="seller-card-actions">
        <button
          className="secondary-btn"
          type="button"
          onClick={() => setIsEditing(true)}
        >
          {isEditing ? "Закрыть" : "Редактировать"}
        </button>
        <button
          className="secondary-btn"
          type="button"
          onClick={() => setBidsOpen(true)}
        >
          Ставки
        </button>
        <button
          className="secondary-btn seller-analysis-btn"
          type="button"
          onClick={() => setAnalysisOpen(true)}
        >
          Расчёты
        </button>
        <button
          className="secondary-btn"
          type="button"
          onClick={finishAuction}
          disabled={auction.status !== "active"}
        >
          {auction.status === "finished" ? "Завершено" : "Завершить"}
        </button>
      </div>

      {actionMessage && <div className="success-box compact">{actionMessage}</div>}

      {isEditing && (
        <div className="seller-modal-backdrop" role="dialog" aria-modal="true">
        <form className="seller-edit-form seller-modal-card" onSubmit={submitEdit}>
          <div className="seller-modal-header">
            <h3>Редактирование лота</h3>
            <button className="secondary-btn" type="button" onClick={() => setIsEditing(false)}>
              Закрыть
            </button>
          </div>
          <div className="field">
            <label>Название</label>
            <input
              name="title"
              value={form.title}
              onChange={updateField}
              disabled={!isActive}
            />
          </div>
          <div className="field">
            <label>Описание</label>
            <textarea name="description" value={form.description} onChange={updateField} />
          </div>
          <div className="field seller-photo-editor">
            <label>Фото лота</label>
            {uniqueEditGallery.length ? (
              <div className="seller-edit-thumbs">
                {uniqueEditGallery.map((url) => (
                  <img src={url} alt={auction.title} key={url} />
                ))}
              </div>
            ) : (
              <p className="field-hint">Фото ещё нет. Добавь одно или несколько изображений.</p>
            )}
            <label className="secondary-btn seller-image-upload-control">
              <span>{imageUploading ? "Загружаем..." : "Добавить фото"}</span>
              <input
                type="file"
                accept="image/*"
                multiple
                disabled={imageUploading}
                onChange={(event) => uploadImages(event.target.files)}
              />
            </label>
          </div>
          <div className="field-row">
            <div className="field">
              <label>Стартовая цена</label>
              <input
                name="start_price"
                type="number"
                value={form.start_price}
                onChange={updateField}
                disabled={!canEditStartPrice}
              />
              {!canEditStartPrice && (
                <p className="field-hint">
                  Стартовая цена фиксируется после первой ставки.
                </p>
              )}
            </div>
            <div className="field">
              <label>Шаг ставки</label>
              <input
                name="recommended_bid_step"
                type="number"
                value={form.recommended_bid_step}
                onChange={updateField}
                disabled={!canEditAuctionRules}
              />
            </div>
          </div>
          <div className="field">
            <label>Дата и время окончания</label>
            <input
              name="end_time"
              type="datetime-local"
              value={form.end_time}
              onChange={updateField}
              disabled={!canEditAuctionRules}
            />
          </div>
          <button className="primary-btn full" type="submit" disabled={saving}>
            {saving ? "Сохраняем..." : "Сохранить изменения"}
          </button>
        </form>
        </div>
      )}

      {analysisOpen && (
        <div className="seller-modal-backdrop" role="dialog" aria-modal="true">
          <div className="seller-modal-card seller-calculation-modal">
            <div className="seller-modal-header">
              <div>
                <p className="modal-eyebrow">Математическая модель</p>
                <h3>Расчёты по лоту</h3>
              </div>
              <button
                className="secondary-btn"
                type="button"
                onClick={() => setAnalysisOpen(false)}
              >
                Закрыть
              </button>
            </div>

            <div className="calculation-grid">
              {calculationRows.map((row) => (
                <div className="calculation-card" key={row.code}>
                  <span className="calculation-code">{row.code}</span>
                  <h4>{row.label}</h4>
                  <strong>{row.value}</strong>
                  <p>{row.description}</p>
                </div>
              ))}
            </div>

            <div className="formula-panel">
              <h4>Формулы и смысл переменных</h4>
              {formulaRows.map((row) => (
                <div className="formula-row" key={row.formula}>
                  <code>{row.formula}</code>
                  <p>{row.text}</p>
                </div>
              ))}
              <p className="calculation-note">
                Эти данные видит только продавец своего лота. Покупателю показываются цена,
                шаг ставки, таймер и публичные характеристики без внутреннего прогноза модели.
              </p>
            </div>
          </div>
        </div>
      )}

      {bidsOpen && (
      <div className="seller-modal-backdrop" role="dialog" aria-modal="true">
      <div className="seller-bids-box seller-modal-card">
        <button className="secondary-btn seller-modal-close" type="button" onClick={() => setBidsOpen(false)}>
          Закрыть
        </button>
        <h4>Ставки покупателей</h4>
        {bids.length ? (
          bids
            .slice()
            .reverse()
            .map((bid) => (
              <div className="seller-bid-row" key={bid.id}>
                <div>
                  <strong>{formatMoney(bid.amount)}</strong>
                  <p>{bid.user}</p>
                </div>
                <button
                  className="primary-btn"
                  type="button"
                  disabled={auction.status !== "active"}
                  onClick={() => acceptBid(bid.id)}
                >
                  Принять
                </button>
              </div>
            ))
        ) : (
          <div className="empty-box compact">Ставок пока нет</div>
        )}
      </div>
      </div>
      )}
    </div>
  );
}

function SellerIncomingOffer({ item, handleOfferDecision }) {
  const [counterAmount, setCounterAmount] = useState(item.offer.counter_amount || "");
  const [actionMessage, setActionMessage] = useState("");
  const isPending = item.offer.status === "pending";

  const decide = async (action) => {
    try {
      const result = await handleOfferDecision(
        item.auction.id,
        item.offer.id,
        action,
        action === "counteroffer" ? counterAmount : null
      );

      if (result) {
        const messages = {
          accept: "Оффер принят. Торги завершены по цене покупателя.",
          reject: "Оффер отклонён.",
          counteroffer: "Встречная цена отправлена покупателю в раздел «Мои офферы».",
        };
        setActionMessage(messages[action]);
      }
    } catch (error) {
      setActionMessage(error.message || "Не удалось сохранить решение");
    }
  };

  return (
    <div className="profile-offer-row">
      <div className="offer-row-main">
        <strong>{item.auction.title}</strong>
        <p>
          {item.offer.user} предлагает {formatMoney(item.offer.amount)}
        </p>
        <p>
          {statusLabel(item.offer.status)} · {recommendationLabel(item.offer.recommendation)}
        </p>
        <p className="offer-decision-note">
          Оффер — предложение покупателя купить лот досрочно. Встречная цена — твоя
          сумма вместо оффера; покупатель увидит её в кабинете и сам примет или отклонит.
        </p>
        {item.offer.counter_amount && (
          <p className="offer-decision-note">
            Последняя встречная цена: <strong>{formatMoney(item.offer.counter_amount)}</strong>
          </p>
        )}
        {actionMessage && <div className="success-box compact">{actionMessage}</div>}
      </div>

      <div className="profile-offer-actions">
        {isPending ? (
          <>
            <div className="field counteroffer-field">
              <label>Встречная цена продавца</label>
              <input
                type="number"
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
              onClick={() => decide("counteroffer")}
              disabled={!counterAmount}
            >
              Отправить встречную цену
            </button>
            <button className="primary-btn" type="button" onClick={() => decide("accept")}>
              Принять оффер
            </button>
          </>
        ) : (
          <span className="profile-status good">Решение сохранено</span>
        )}
      </div>
    </div>
  );
}

function BuyerOfferCard({ item, handleSelectAuction, handleBuyerOfferDecision }) {
  const [actionMessage, setActionMessage] = useState("");
  const offer = item.offer;
  const isCounteroffer = offer.status === "counteroffer" && offer.counter_amount;

  const answerCounteroffer = async (action) => {
    try {
      await handleBuyerOfferDecision(item.auction.id, offer.id, action);
      setActionMessage(
        action === "accept"
          ? "Встречная цена принята. Торги завершены по цене продавца."
          : "Встречная цена отклонена."
      );
    } catch (error) {
      setActionMessage(error.message || "Не удалось сохранить ответ");
    }
  };

  return (
    <div className={`profile-offer-card offer-stage-${offer.status}`} key={offer.id}>
      <AuctionMiniCard auction={item.auction} onOpen={handleSelectAuction} />
      <div className="profile-row">
        <span>Твой оффер</span>
        <strong>{formatMoney(offer.amount)}</strong>
      </div>
      <div className="offer-stage-pill">{offerStageLabel(offer, "buyer")}</div>

      {offer.status === "pending" && (
        <p className="offer-decision-note">
          Предложение уже отправлено продавцу и находится у него в разделе «Входящие офферы».
          Пока продавец не выбрал действие, аукцион продолжается.
        </p>
      )}

      {isCounteroffer && (
        <>
          <p className="offer-decision-note">
            Продавец не принял исходную сумму и предложил свою встречную цену:{" "}
            <strong>{formatMoney(offer.counter_amount)}</strong>. Если ты примешь её,
            торги завершатся по этой цене.
          </p>
          <div className="profile-offer-actions buyer-counter-actions">
            <button
              className="primary-btn"
              type="button"
              onClick={() => answerCounteroffer("accept")}
            >
              Принять встречную цену
            </button>
            <button
              className="secondary-btn"
              type="button"
              onClick={() => answerCounteroffer("reject")}
            >
              Отклонить
            </button>
          </div>
        </>
      )}

      {offer.status === "accepted" && (
        <p className="offer-decision-note">
          Оффер принят. Лот завершён, итоговая цена зафиксирована.
        </p>
      )}

      {offer.status === "rejected" && (
        <p className="offer-decision-note">
          Оффер отклонён. Можно продолжить участие через обычные ставки, если торги активны.
        </p>
      )}

      {actionMessage && <div className="success-box compact">{actionMessage}</div>}
    </div>
  );
}

function SellerProcessedOffer({ item }) {
  const offer = item.offer;
  return (
    <div className={`profile-offer-row processed offer-stage-${offer.status}`}>
      <div className="offer-row-main">
        <strong>{item.auction.title}</strong>
        <p>
          {offer.user} предлагал {formatMoney(offer.amount)}
        </p>
        <div className="offer-stage-pill">{offerStageLabel(offer, "seller")}</div>
        {offer.status === "counteroffer" && offer.counter_amount && (
          <p className="offer-decision-note">
            Встречная цена продавца {formatMoney(offer.counter_amount)} отправлена покупателю
            в раздел «Мои офферы». Теперь следующий ход за покупателем.
          </p>
        )}
        {offer.status === "accepted" && (
          <p className="offer-decision-note">Оффер принят, торги завершены по цене оффера.</p>
        )}
        {offer.status === "rejected" && (
          <p className="offer-decision-note">Оффер отклонён продавцом.</p>
        )}
      </div>
    </div>
  );
}

function ProfilePage({
  currentUserName,
  profileMode,
  setProfileMode,
  profileData,
  profileLoading,
  profileError,
  profileMessage,
  avatarUrl,
  avatarLoading,
  avatarError,
  handleAvatarUpload,
  handleProfileUpdate,
  handleSelectAuction,
  handleOfferDecision,
  handleBuyerOfferDecision,
  handleUpdateAuction,
  handleUploadAuctionImages,
  handleAcceptBid,
  goToSell,
  goToOffers,
}) {
  const buyerStats = profileData?.buyer?.stats || {};
  const sellerStats = profileData?.seller?.stats || {};
  const buyerBids = profileData?.buyer?.bids || [];
  const sentOffers = profileData?.buyer?.offers || [];
  const sellerListings = profileData?.seller?.listings || [];
  const incomingOffers = profileData?.seller?.incoming_offers || [];
  const pendingIncomingOffers = incomingOffers.filter(
    (item) => item.offer.status === "pending"
  );
  const processedIncomingOffers = incomingOffers.filter(
    (item) => item.offer.status !== "pending"
  );

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
          <div className="profile-avatar">
            {avatarUrl ? (
              <img src={avatarUrl} alt={currentUserName} />
            ) : (
              (currentUserName || "U").slice(0, 1)
            )}
          </div>
          <h3>{currentUserName}</h3>
          <p>Покупатель и продавец</p>

          <label className="avatar-upload-control">
            <span>
              {avatarLoading
                ? "Загружаем..."
                : avatarUrl
                ? "Изменить аватар"
                : "Добавить аватар"}
            </span>
            <input
              type="file"
              accept="image/*"
              disabled={avatarLoading}
              onChange={(e) => handleAvatarUpload(e.target.files)}
            />
          </label>

          {avatarError && <div className="error-box compact">{avatarError}</div>}

          <ProfileEditor
            user={profileData?.user}
            profileMessage={profileMessage}
            handleProfileUpdate={handleProfileUpdate}
          />

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
          <button className="secondary-btn full" type="button" onClick={goToOffers}>
            Офферы
          </button>
        </aside>

        <main className="profile-content">
          {profileMode === "buyer" ? (
            <>
              <div className="profile-stats-grid">
                <StatCard label="Аукционы со ставками" value={buyerStats.active_bids || 0} />
                <StatCard label="Активно лидирую" value={buyerStats.leading_bids || 0} />
                <StatCard label="Отправлено офферов" value={buyerStats.sent_offers || 0} />
                <StatCard label="Офферы ждут ответа" value={buyerStats.pending_offers || 0} />
              </div>

              <section className="profile-panel">
                <div className="panel-header">
                  <h3>Мои ставки</h3>
                </div>

                <div className="profile-list-grid">
                  {buyerBids.map((item) => {
                    const status = buyerBidStatus(item);
                    return (
                      <div className="profile-bid-card" key={item.auction.id}>
                        <AuctionMiniCard auction={item.auction} onOpen={handleSelectAuction} />
                        <div className="profile-row">
                          <span>Моя последняя ставка</span>
                          <strong>{formatMoney(item.my_last_bid.amount)}</strong>
                        </div>
                        <div className={`profile-status ${status.className}`}>
                          {status.label}
                        </div>
                      </div>
                    );
                  })}

                  {!buyerBids.length && (
                    <div className="empty-box">Ты пока не делал ставки</div>
                  )}
                </div>
              </section>

              <section className="profile-panel">
                <div className="panel-header">
                  <h3>Мои офферы</h3>
                </div>
                <OfferFlowHint role="buyer" />

                <div className="profile-list-grid">
                  {sentOffers.map((item) => (
                    <BuyerOfferCard
                      key={item.offer.id}
                      item={item}
                      handleSelectAuction={handleSelectAuction}
                      handleBuyerOfferDecision={handleBuyerOfferDecision}
                    />
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
                    <SellerListingCard
                      key={auction.id}
                      auction={auction}
                      handleSelectAuction={handleSelectAuction}
                      handleUpdateAuction={handleUpdateAuction}
                      handleUploadAuctionImages={handleUploadAuctionImages}
                      handleAcceptBid={handleAcceptBid}
                    />
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
                <OfferFlowHint role="seller" />

                <div className="profile-offers-table">
                  {pendingIncomingOffers.map((item) => (
                    <SellerIncomingOffer
                      key={item.offer.id}
                      item={item}
                      handleOfferDecision={handleOfferDecision}
                    />
                  ))}

                  {!pendingIncomingOffers.length && (
                    <div className="empty-box">
                      Новых входящих офферов нет. Обработанные решения показаны ниже.
                    </div>
                  )}
                </div>
              </section>

              <section className="profile-panel">
                <div className="panel-header">
                  <h3>История офферов</h3>
                </div>

                <div className="profile-offers-table">
                  {processedIncomingOffers.map((item) => (
                    <SellerProcessedOffer key={item.offer.id} item={item} />
                  ))}

                  {!processedIncomingOffers.length && (
                    <div className="empty-box">Обработанных офферов пока нет</div>
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
