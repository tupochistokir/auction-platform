import { useMemo, useState } from "react";
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
};

const subcategoryIcon = (value) => (value || "?").slice(0, 1).toUpperCase();

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
      icon: subcategoryIcon(subcategory.value),
      level: "child",
      parent: category.value,
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
  const [expandedCategory, setExpandedCategory] = useState("");
  const [mobileCategoriesOpen, setMobileCategoriesOpen] = useState(false);
  const categories = useMemo(() => flattenCategories(), []);
  const visibleCategories = useMemo(() => {
    const items = [{ value: "", label: "Все лоты", icon: categoryIcons.all, level: "root" }];
    categoryOptions.forEach((category) => {
      items.push({
        value: category.value,
        label: category.label,
        icon: categoryIcons[category.value] || "◇",
        level: "root",
        hasChildren: Boolean(category.subcategories?.length),
      });
      if (expandedCategory === category.value) {
        category.subcategories?.forEach((subcategory) => {
          items.push({
            value: subcategory.value,
            label: subcategory.label,
            icon: subcategoryIcon(subcategory.value),
            level: "child",
            parent: category.value,
          });
        });
      }
    });
    return items;
  }, [expandedCategory]);
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

  const selectCategory = (category) => {
    if (category.level === "root" && category.value) {
      setExpandedCategory((current) =>
        current === category.value ? "" : category.value
      );
    }
    handleCategorySelect(category.value);
    if (category.level === "child" || category.value === "") {
      setMobileCategoriesOpen(false);
    }
  };

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
        <aside className={`category-sidebar ${mobileCategoriesOpen ? "open" : ""}`}>
          <button
            className="category-panel-toggle"
            type="button"
            onClick={() => setMobileCategoriesOpen((current) => !current)}
          >
            Категории
            <span>{mobileCategoriesOpen ? "−" : "+"}</span>
          </button>
          <div className="sidebar-title">Категории</div>

          <div className="sidebar-list">
            {visibleCategories.map((category, index) => (
              <button
                key={`${category.level}-${category.value || "all"}-${index}`}
                className={`sidebar-item ${category.level} ${
                  filters.category === category.value ? "active" : ""
                } ${expandedCategory === category.value ? "expanded" : ""}`}
                type="button"
                onClick={() => selectCategory(category)}
              >
                <span className="sidebar-icon">{category.icon}</span>
                <span>{category.label}</span>
                {category.hasChildren && (
                  <span className="sidebar-arrow">
                    {expandedCategory === category.value ? "−" : "+"}
                  </span>
                )}
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
