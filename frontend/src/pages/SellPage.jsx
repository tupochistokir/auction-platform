import { useState } from "react";
import { brandOptions } from "../data/brands";
import { categoryOptions } from "../data/categories";
import { colorOptions } from "../data/colors";
import { sizeOptions } from "../data/sizes";
import { materialOptions } from "../data/materials";
import { styleOptions } from "../data/styles";
import { conditionOptions } from "../data/conditions";
import SmartBrandInput from "../components/SmartBrandInput";
import MultiColorSelect from "../components/MultiColorSelect";

const formatMoney = (value) => {
  const number = Number(value);
  return Number.isFinite(number) ? `${Math.round(number).toLocaleString("ru-RU")} ₽` : "—";
};

const formatScore = (value) =>
  typeof value === "number" ? value.toFixed(4) : "—";

function SellPage({
  sellForm,
  handleCreateAuction,
  handleSellTopLevelChange,
  handleSellQuestionnaireChange,
  handleImageUpload,
  sellImages,
  handleEstimateSell,
  sellLoading,
  sellError,
  sellResult,
  selectedCategory,
  availableSubcategories,
  handleToggleColor,
  handleApplyPricingRecommendation,
}) {
  const [qOpen, setQOpen] = useState(false);
  const [formulasOpen, setFormulasOpen] = useState(false);
  const analysis = sellResult?.analysis || {};
  const formulaExplanation =
    sellResult?.formula_explanation || analysis.formula_explanation || {};

  const scoreRows = [
    ["Q", "Подтверждённая ценность", analysis.confirmed_value_score],
    ["A_pre", "Потенциал до старта", analysis.auction_potential_pre],
    ["D", "Спрос", analysis.demand_score],
    ["I", "Интерес", analysis.interest_score],
    ["V", "Неопределённость", analysis.uncertainty_score],
  ];

  const qRows = [
    ["Q_b", "Бренд", analysis.brand_score],
    ["Q_c", "Состояние", analysis.condition_score],
    ["Q_v", "Винтажность", analysis.vintage_score],
    ["Q_r", "Редкость", analysis.rarity_score],
  ];

  const formulaRows = [
    ["Q", formulaExplanation.confirmed_value_score],
    ["A_pre", formulaExplanation.auction_potential_pre],
    ["P_base", formulaExplanation.base_price],
    ["P_start", formulaExplanation.start_price],
    ["Step", formulaExplanation.bid_step],
    ["E[P_final]", formulaExplanation.expected_final_price],
  ].filter(([, formula]) => Boolean(formula));

  return (
    <>
      <section className="hero-banner sell-hero">
        <div>
          <p className="hero-label">Размещение товара</p>
          <h2>Продажа вещи через умный аукцион</h2>
          <p>
            Заполни анкету товара, загрузи фото и получи рекомендации системы по
            запуску аукциона.
          </p>
        </div>
      </section>

      <div className="layout sell-layout">
        <section className="catalog-panel sell-form-panel">
          <div className="panel-header">
            <h3>Анкета продавца</h3>
          </div>

          <form onSubmit={handleEstimateSell}>
            <div className="field">
              <label>Название товара</label>
              <input
                name="title"
                value={sellForm.title}
                onChange={handleSellTopLevelChange}
                placeholder="Например: Винтажный бомбер"
              />
            </div>

            <div className="field">
              <label>Продавец</label>
              <input
                name="seller_name"
                value={sellForm.seller_name}
                readOnly
              />
            </div>

            <div className="field">
              <label>Желаемая цена продавца</label>
              <input
                type="text"
                inputMode="numeric"
                name="start_price"
                value={sellForm.start_price}
                onChange={handleSellTopLevelChange}
                placeholder="Например 3000"
              />
            </div>

            <div className="field">
              <label>Окончание аукциона</label>
              <input
                type="datetime-local"
                name="end_time"
                value={sellForm.end_time || ""}
                onChange={handleSellTopLevelChange}
              />
              <p className="field-hint">
                Выбери дату и время по календарю: до этого момента лот будет принимать ставки.
              </p>
            </div>

            <div className="field">
              <label>Описание</label>
              <textarea
                name="description"
                value={sellForm.description}
                onChange={handleSellTopLevelChange}
                placeholder="Кратко опиши вещь"
              />
            </div>

            <div className="field">
              <label>Фотографии товара</label>
              <input
                type="file"
                multiple
                accept="image/*"
                onChange={(e) => handleImageUpload(e.target.files)}
              />
            </div>

            {sellImages.length > 0 && (
              <div className="image-preview-grid">
                {sellImages.map((image, index) => (
                  <div className="image-preview-card" key={index}>
                    <img src={image.url} alt={image.name} />
                    <span>{image.name}</span>
                  </div>
                ))}
              </div>
            )}

            <div className="field">
              <label>Бренд</label>
              <SmartBrandInput
                value={sellForm.questionnaire.brand}
                onChange={handleSellQuestionnaireChange}
                options={brandOptions}
              />
            </div>

            <div className="field-row">
              <div className="field">
                <label>Категория</label>
                <select
                  name="category"
                  value={sellForm.questionnaire.category}
                  onChange={handleSellQuestionnaireChange}
                >
                  <option value="">Выбери категорию</option>
                  {categoryOptions.map((item) => (
                    <option key={item.value} value={item.value}>
                      {item.label}
                    </option>
                  ))}
                </select>
              </div>
            
              <div className="field">
                <label>Подкатегория</label>
                <select
                  name="subcategory"
                  value={sellForm.questionnaire.subcategory || ""}
                  onChange={handleSellQuestionnaireChange}
                  disabled={!selectedCategory}
                >
                  <option value="">Выбери подкатегорию</option>
                  {availableSubcategories.map((item) => (
                    <option key={item.value} value={item.value}>
                      {item.label}
                    </option>
                  ))}
                </select>
              </div>
            </div>
            
            <div className="field">
              <label>Стиль</label>
              <select
                name="style"
                value={sellForm.questionnaire.style}
                onChange={handleSellQuestionnaireChange}
              >
                <option value="">Выбери стиль</option>
                {styleOptions.map((style) => (
                  <option key={style} value={style}>
                    {style}
                  </option>
                ))}
              </select>
            </div>

            <div className="field size-field">
              <label>Размер</label>
              <select
                name="size"
                value={sellForm.questionnaire.size}
                onChange={handleSellQuestionnaireChange}
              >
                <option value="">Выбери размер</option>
                {sizeOptions.map((size) => (
                  <option key={size} value={size}>
                    {size}
                  </option>
                ))}
              </select>
            </div>

            <div className="field color-field">
              <label>Цвета товара</label>
              <MultiColorSelect
                options={colorOptions}
                selectedColors={sellForm.questionnaire.colors || []}
                onToggleColor={handleToggleColor}
              />
            </div>

            <div className="field-row">
              <div className="field">
                <label>Материал</label>
                <select
                  name="material"
                  value={sellForm.questionnaire.material}
                  onChange={handleSellQuestionnaireChange}
                >
                  <option value="">Выбери материал</option>
                  {materialOptions.map((material) => (
                    <option key={material} value={material}>
                      {material}
                    </option>
                  ))}
                </select>
              </div>

              <div className="field">
                <label>Состояние</label>
                <select
                  name="condition"
                  value={sellForm.questionnaire.condition}
                  onChange={handleSellQuestionnaireChange}
                >
                  {conditionOptions.map((condition) => (
                    <option key={condition.value} value={condition.value}>
                      {condition.label}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <div className="field">
              <label>Возраст вещи (лет)</label>
              <input
                type="text"
                inputMode="numeric"
                name="estimated_age"
                value={sellForm.questionnaire.estimated_age}
                onChange={handleSellQuestionnaireChange}
                placeholder="Например 7"
              />
            </div>

            <div className="checkbox-field">
              <input
                type="checkbox"
                name="has_tag"
                checked={sellForm.questionnaire.has_tag}
                onChange={handleSellQuestionnaireChange}
              />
              <span>Есть оригинальная бирка</span>
            </div>

            <div className="field">
              <label>Дефекты</label>
              <input
                name="defects"
                value={sellForm.questionnaire.defects}
                onChange={handleSellQuestionnaireChange}
              />
            </div>

            <div className="field">
              <label>Комментарий продавца</label>
              <textarea
                name="seller_comment"
                value={sellForm.questionnaire.seller_comment}
                onChange={handleSellQuestionnaireChange}
              />
            </div>

            <button type="submit" className="primary-btn full" disabled={sellLoading}>
              {sellLoading ? "Считаем..." : "Рассчитать аукцион"}
            </button>
          </form>
        </section>

        <section className="auction-panel">
          <div className="auction-card">
            <div className="panel-header">
              <h3>Рекомендации продавцу</h3>
            </div>

            {sellError && <div className="error-box">{sellError}</div>}

            {!sellResult && !sellError && (
              <div className="empty-box">
                Заполни анкету товара и нажми «Рассчитать аукцион»
              </div>
            )}

            {sellResult && (
              <div className="sell-result-content">
                <div className="auction-stats-grid">
                  <div className="stat-box">
                    <span>Базовая цена</span>
                    <strong>{formatMoney(sellResult.base_price)}</strong>
                  </div>
                  <div className="stat-box">
                    <span>Стартовая цена</span>
                    <strong>{formatMoney(sellResult.recommended_start_price)}</strong>
                  </div>
                  <div className="stat-box">
                    <span>Шаг ставки</span>
                    <strong>{formatMoney(sellResult.recommended_bid_step)}</strong>
                  </div>
                  <div className="stat-box">
                    <span>Прогноз финальной цены</span>
                    <strong>{formatMoney(sellResult.expected_final_price)}</strong>
                  </div>
                  <div className="stat-box stat-box-wide">
                    <span>Диапазон финальной цены</span>
                    <strong>
                      {formatMoney(sellResult.conservative_final_price)} —{" "}
                      {formatMoney(sellResult.optimistic_final_price)}
                    </strong>
                  </div>
                </div>
                <p className="seller-recommendation-note">
                  После публикации на прогноз цены будет влиять активность покупателей:
                  просмотры, лайки, избранное, офферы, ставки и темп роста текущей цены.
                </p>

                <div className="result-box">
                  <h4>Математический разбор</h4>
                  <div className="score-grid">
                    {scoreRows.map(([code, label, value]) => (
                      <div className="score-card" key={code}>
                        <span>{code}</span>
                        <strong>{formatScore(value)}</strong>
                        <p>{label}</p>
                      </div>
                    ))}
                  </div>
                  <button
                    className="secondary-btn full result-toggle-btn"
                    type="button"
                    onClick={() => setQOpen((current) => !current)}
                  >
                    Подтверждённая ценность Q {qOpen ? "−" : "+"}
                  </button>
                  {qOpen && (
                    <div className="score-grid nested-score-grid">
                      {qRows.map(([code, label, value]) => (
                        <div className="score-card" key={code}>
                          <span>{code}</span>
                          <strong>{formatScore(value)}</strong>
                          <p>{label}</p>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                <div className="result-box">
                  <button
                    className="secondary-btn full result-toggle-btn"
                    type="button"
                    onClick={() => setFormulasOpen((current) => !current)}
                  >
                    Математические формулы {formulasOpen ? "−" : "+"}
                  </button>
                  {formulasOpen && (
                    <div className="formula-list">
                      {formulaRows.map(([code, formula]) => (
                        <div className="formula-row" key={code}>
                          <span>{code}</span>
                          <p>{formula}</p>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                <div className="result-box">
                  <h4>Рекомендация системы</h4>
                  <p>
                    Для этого товара рекомендуется запускать аукцион со стартовой
                    цены <strong>{formatMoney(sellResult.recommended_start_price)}</strong>,
                    использовать шаг ставки{" "}
                    <strong>{formatMoney(sellResult.recommended_bid_step)}</strong> и
                    ориентироваться на итоговую цену около{" "}
                    <strong>{formatMoney(sellResult.expected_final_price)}</strong>.
                  </p>
                  <p>
                    Цена, которую указал продавец, не заменяется автоматически:
                    рекомендацию модели можно применить только вручную в финальных
                    параметрах публикации.
                  </p>
                </div>

                <div className="result-box publish-settings-box">
                  <h4>Финальные параметры публикации</h4>
                  <p>
                    Рекомендации можно принять как есть или вручную скорректировать
                    стартовую цену и шаг ставки перед запуском.
                  </p>

                  <div className="field-row">
                    <div className="field">
                      <label>Финальная стартовая цена</label>
                      <input
                        type="text"
                        inputMode="numeric"
                        name="start_price"
                        value={sellForm.start_price}
                        onChange={handleSellTopLevelChange}
                        placeholder="Например 3000"
                      />
                    </div>

                    <div className="field">
                      <label>Финальный шаг ставки</label>
                      <input
                        type="text"
                        inputMode="numeric"
                        name="bid_step_override"
                        value={sellForm.bid_step_override || ""}
                        onChange={handleSellTopLevelChange}
                        placeholder="Например 150"
                      />
                    </div>
                  </div>

                  <div className="field">
                    <label>Финальное время окончания</label>
                    <input
                      type="datetime-local"
                      name="end_time"
                      value={sellForm.end_time || ""}
                      onChange={handleSellTopLevelChange}
                    />
                    <p className="field-hint">
                      Можно изменить длительность торгов перед публикацией.
                    </p>
                  </div>

                  <button
                    type="button"
                    className="secondary-btn full"
                    onClick={handleApplyPricingRecommendation}
                  >
                    Применить рекомендации модели
                  </button>
                </div>
                {sellResult && (
                  <button
                    className="primary-btn full"
                    onClick={handleCreateAuction}
                  >
                    Опубликовать аукцион
                  </button>
                )}
              </div>
            )}
          </div>
        </section>
      </div>
    </>
  );
}

export default SellPage;
