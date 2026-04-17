function CatalogPage({
  error,
  loading,
  filters,
  handleFilterChange,
  filteredAuctions,
  handleSelectAuction,
}) {
  const categories = [
    "Распродажа",
    "Верхняя одежда",
    "Куртки",
    "Пальто",
    "Худи",
    "Футболки",
    "Рубашки",
    "Джинсы",
    "Брюки",
    "Кроссовки",
    "Аксессуары",
    "Винтаж",
    "Streetwear",
    "Бренды",
  ];

  return (
    <>
      <section className="hero-banner marketplace-hero">
        <div>
          <p className="hero-label">Главная страница</p>
          <h2>Рекомендованные товары и живые аукционы</h2>
          <p>
            Листай товары как в маркетплейсе, открывай карточку и участвуй в торгах.
          </p>
        </div>
      </section>

      {error && <div className="error-box">{error}</div>}

      <div className="market-layout">
        <aside className="category-sidebar">
          <div className="sidebar-title">Категории</div>

          <div className="sidebar-list">
            {categories.map((category) => (
              <button key={category} className="sidebar-item">
                {category}
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
              name="brand"
              value={filters.brand}
              onChange={handleFilterChange}
              placeholder="Бренд"
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
              {filteredAuctions.map((auction) => (
                <button
                  key={auction.id}
                  className="market-card"
                  onClick={() => handleSelectAuction(auction)}
                >
                  <div className="market-card-image">
                    {auction.image_url ? (
                      <img src={auction.image_url} alt={auction.title} className="market-card-img" />
                    ) : null}
                  
                    <div className="market-badge">
                      {auction.status === "active" ? "Аукцион" : "Завершён"}
                    </div>
                  </div>

                  <div className="market-card-body">
                    <p className="market-brand">{auction.brand}</p>
                    <h4>{auction.title}</h4>

                    <div className="market-price-row">
                      <strong>{auction.current_price} ₽</strong>
                      <span>шаг {auction.recommended_bid_step} ₽</span>
                    </div>
                  </div>
                </button>
              ))}

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