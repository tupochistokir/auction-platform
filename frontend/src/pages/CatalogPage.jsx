import { categoryOptions } from "../data/categories";

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

const categoryIcons = {
  all: "◇",
  outerwear: "♜",
  tops: "◌",
  bottoms: "▥",
  shoes: "♢",
  accessories: "✦",
  bomber: "B",
  leather_jacket: "L",
  denim_jacket: "D",
  windbreaker: "W",
  puffer: "P",
  sheepskin: "S",
  coat: "C",
  trench: "T",
  hoodie: "H",
  tshirt: "T",
  shirt: "S",
  sweater: "W",
  longsleeve: "L",
  jeans: "J",
  pants: "P",
  shorts: "S",
  skirt: "K",
  sneakers: "S",
  boots: "B",
  loafers: "L",
  bag: "B",
  cap: "C",
  belt: "B",
  scarf: "S",
};

const flattenCategories = () => [
  { value: "", label: "Все лоты", icon: categoryIcons.all, level: "root" },
  ...categoryOptions.flatMap((category) => [
    {
      value: category.value,
      label: category.label,
      icon: categoryIcons[category.value] || "◇",
      level: "root",
    },
    ...(category.subcategories || []).map((subcategory) => ({
      value: subcategory.value,
      label: subcategory.label,
      icon: categoryIcons[subcategory.value] || "·",
      level: "child",
    })),
  ]),
];

function CatalogPage({
  error,
  loading,
  filters,
  handleFilterChange,
  handleCategorySelect,
  filteredAuctions,
  handleSelectAuction,
}) {
  const categories = flattenCategories();
  const activeCategory =
    categories.find((category) => category.value === filters.category) || categories[0];
  const heroTitle =
    activeCategory.value === ""
      ? "Рекомендованные товары и живые аукционы"
      : activeCategory.label;
  const heroSubtitle =
    activeCategory.value === ""
      ? "Листай товары как в премиальном винтажном каталоге, открывай карточку и участвуй в торгах."
      : `Раздел каталога: ${activeCategory.label}. Фильтр работает как отдельная страница категории.`;

  return (
    <>
      <section className="hero-banner marketplace-hero">
        <div>
          <p className="hero-label">Главная страница</p>
          <h2>{heroTitle}</h2>
          <p>{heroSubtitle}</p>
        </div>
      </section>

      {error && <div className="error-box">{error}</div>}

      <div className="market-layout">
        <aside className="category-sidebar">
          <div className="sidebar-title">Категории</div>

          <div className="sidebar-list">
            {categories.map((category, index) => (
              <button
                key={`${category.level}-${category.value || "all"}-${index}`}
                className={`sidebar-item ${category.level} ${
                  filters.category === category.value ? "active" : ""
                }`}
                type="button"
                onClick={() => handleCategorySelect(category.value)}
              >
                <span className="sidebar-icon">{category.icon}</span>
                <span>{category.label}</span>
              </button>
            ))}
          </div>
        </aside>

        <main className="market-content">
          <div className="market-filters">
            <input
              name="search"
              value={filters.search}
              onChange={handleFilterChange}
              placeholder="Поиск по товарам"
            />

            <input
              type="number"
              name="minPrice"
              value={filters.minPrice}
              onChange={handleFilterChange}
              placeholder="Цена от"
            />

            <input
              type="number"
              name="maxPrice"
              value={filters.maxPrice}
              onChange={handleFilterChange}
              placeholder="Цена до"
            />
          </div>

          {loading ? (
            <div className="empty-box">Загружаем товары...</div>
          ) : (
            <div className="market-grid">
              {filteredAuctions.map((auction) => {
                const image = auction.image_urls?.[0] || auction.image_url;
                const questionnaire = auction.questionnaire || {};
                const categoryLabel =
                  categories.find((category) => category.value === questionnaire.subcategory)
                    ?.label ||
                  categories.find((category) => category.value === questionnaire.category)
                    ?.label ||
                  "Аукцион";

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
                        <div className="market-card-placeholder">Vintage Market</div>
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
                        <span>{categoryLabel}</span>
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

              {!filteredAuctions.length && (
                <div className="empty-box">По фильтрам ничего не найдено</div>
              )}
            </div>
          )}
        </main>
      </div>
    </>
  );
}

export default CatalogPage;
