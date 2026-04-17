import { useEffect, useMemo, useState } from "react";

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

  useEffect(() => {
    setSelectedImage(images[0] || null);
  }, [images]);

  if (!selectedAuction) {
    return <div className="empty-box">Товар не выбран</div>;
  }

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
            {selectedImage ? (
              <img
                src={selectedImage}
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
                className={`product-thumb ${selectedImage === img ? "active" : ""}`}
                onClick={() => setSelectedImage(img)}
              >
                <img src={img} alt={`thumb-${index}`} className="product-thumb-img" />
              </button>
            ))}
          </div>
        </section>

        <section className="product-info-panel">
          <div className="auction-price-box large">
            <span>Текущая цена</span>
            <strong>{selectedAuction.current_price} ₽</strong>
          </div>

          <div className="auction-stats-grid product-stats">
            <div className="stat-box">
              <span>Шаг ставки</span>
              <strong>{selectedAuction.recommended_bid_step} ₽</strong>
            </div>
            <div className="stat-box">
              <span>Статус</span>
              <strong>
                {selectedAuction.status === "active" ? "Идут торги" : "Завершён"}
              </strong>
            </div>
            <div className="stat-box">
              <span>Количество ставок</span>
              <strong>{selectedAuction.bids.length}</strong>
            </div>
            <div className="stat-box">
              <span>Минимальная ставка</span>
              <strong>
                {(
                  selectedAuction.current_price +
                  selectedAuction.recommended_bid_step
                ).toFixed(2)} ₽
              </strong>
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
                disabled={bidLoading}
              >
                {bidLoading ? "Отправляем ставку..." : "Подтвердить ставку"}
              </button>
            </form>
          </div>
        </section>
      </div>

      <section className="bids-history-card">
        <h3>История ставок</h3>

        <div className="bids-list">
          {selectedAuction.bids
            .slice()
            .reverse()
            .map((bid, index) => (
              <div className="bid-item" key={index}>
                <div>
                  <strong>{bid.user}</strong>
                  <p>Ставка участника</p>
                </div>
                <span>{bid.amount} ₽</span>
              </div>
            ))}
        </div>
      </section>
    </>
  );
}

export default ProductPage;