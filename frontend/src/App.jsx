import { useCallback, useEffect, useMemo, useState } from "react";
import "./App.css";
import Header from "./components/Header";
import CatalogPage from "./pages/CatalogPage";
import SellPage from "./pages/SellPage";
import { categoryOptions } from "./data/categories";
import ProductPage from "./pages/ProductPage";
import ProfilePage from "./pages/ProfilePage";

function App() {
  const [page, setPage] = useState("catalog");
  const [catalogView, setCatalogView] = useState("grid");
  const [auctions, setAuctions] = useState([]);
  const [selectedAuction, setSelectedAuction] = useState(null);
  const [currentUserName, setCurrentUserName] = useState("Кирилл");
  const [profileMode, setProfileMode] = useState("buyer");
  const [profileData, setProfileData] = useState(null);
  const [profileLoading, setProfileLoading] = useState(false);
  const [profileError, setProfileError] = useState("");

  const [filters, setFilters] = useState({
    brand: "",
    minPrice: "",
    maxPrice: "",
    search: "",
    category: "",
  });

  const [bidUser, setBidUser] = useState("Кирилл");
  const [bidAmount, setBidAmount] = useState("");
  const [userValue, setUserValue] = useState("");
  const [offerAmount, setOfferAmount] = useState("");

  const [loading, setLoading] = useState(false);
  const [bidLoading, setBidLoading] = useState(false);
  const [recommendationLoading, setRecommendationLoading] = useState(false);
  const [offerLoading, setOfferLoading] = useState(false);
  const [error, setError] = useState("");
  const [bidError, setBidError] = useState("");
  const [recommendationError, setRecommendationError] = useState("");
  const [offerError, setOfferError] = useState("");
  const [successMessage, setSuccessMessage] = useState("");
  const [bidRecommendation, setBidRecommendation] = useState(null);
  const [offerResult, setOfferResult] = useState(null);

  const [sellForm, setSellForm] = useState({
    title: "",
    seller_name: "Кирилл",
    start_price: 3000,
    bid_step_override: "",
    description: "",
    image_url: "",
    image_urls: [],
    questionnaire: {
      brand: "",
      category: "",
      subcategory: "",
      size: "",
      colors: [],
      material: "",
      condition: "good",
      has_tag: false,
      estimated_age: 0,
      defects: "",
      seller_comment: "",
      style: "",
    },
  });

  const [sellImages, setSellImages] = useState([]);
  const [sellResult, setSellResult] = useState(null);
  const [sellLoading, setSellLoading] = useState(false);
  const [sellError, setSellError] = useState("");

  useEffect(() => {
    setBidUser(currentUserName);
    setSellForm((prev) => ({
      ...prev,
      seller_name: currentUserName,
    }));
  }, [currentUserName]);

  const loadAuctions = useCallback(async () => {
    try {
      setLoading(true);
      setError("");

      const response = await fetch("http://127.0.0.1:8000/auctions/");
      if (!response.ok) {
        throw new Error("Ошибка загрузки аукционов");
      }

      const data = await response.json();
      setAuctions(data.auctions);

      setSelectedAuction((currentAuction) => {
        if (!currentAuction && data.auctions.length > 0) {
          return data.auctions[0];
        }

        if (currentAuction) {
          return data.auctions.find((a) => a.id === currentAuction.id) || currentAuction;
        }

        return currentAuction;
      });
    } catch {
      setError("Не удалось загрузить аукционы. Проверь, запущен ли backend.");
    } finally {
      setLoading(false);
    }
  }, []);

  const loadAuctionById = async (auctionId) => {
    try {
      setBidError("");
      setSuccessMessage("");

      const response = await fetch(`http://127.0.0.1:8000/auctions/${auctionId}`);
      if (!response.ok) {
        throw new Error("Ошибка загрузки аукциона");
      }

      const data = await response.json();
      setSelectedAuction(data);

      const minBid = Number(data.current_price || 0) + Number(data.recommended_bid_step || 0);
      setBidAmount(minBid.toFixed(2));
      setUserValue(Number(data.expected_final_price || minBid).toFixed(2));
      setOfferAmount(Number(data.expected_final_price || minBid).toFixed(2));
      setBidRecommendation(null);
      setOfferResult(null);
    } catch {
      setBidError("Не удалось открыть аукцион");
    }
  };

  const loadProfile = useCallback(async () => {
    if (!currentUserName.trim()) return;

    try {
      setProfileLoading(true);
      setProfileError("");

      const response = await fetch(
        `http://127.0.0.1:8000/auctions/profile/${encodeURIComponent(currentUserName)}`
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Ошибка загрузки профиля");
      }

      setProfileData(data);
    } catch (err) {
      setProfileError(err.message || "Не удалось загрузить личный кабинет");
    } finally {
      setProfileLoading(false);
    }
  }, [currentUserName]);

  useEffect(() => {
    loadAuctions();
  }, [loadAuctions]);

  useEffect(() => {
    if (page === "profile") {
      loadProfile();
    }
  }, [page, loadProfile]);

  useEffect(() => {
    if (selectedAuction) {
      const minBid =
        Number(selectedAuction.current_price || 0) +
        Number(selectedAuction.recommended_bid_step || 0);
      setBidAmount(minBid.toFixed(2));
      setUserValue(Number(selectedAuction.expected_final_price || minBid).toFixed(2));
      setOfferAmount(Number(selectedAuction.expected_final_price || minBid).toFixed(2));
      setRecommendationError("");
      setOfferError("");
    }
  }, [selectedAuction]);

  const handleSelectAuction = async (auction) => {
    await loadAuctionById(auction.id);
    setCatalogView("product");
  };

  const handleOpenAuctionFromProfile = async (auction) => {
    await handleSelectAuction(auction);
    setPage("catalog");
  };

  const handlePlaceBid = async (e) => {
    e.preventDefault();
    if (!selectedAuction) return;

    try {
      setBidLoading(true);
      setBidError("");
      setSuccessMessage("");

      const response = await fetch(
        `http://127.0.0.1:8000/auctions/${selectedAuction.id}/bid`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            user: bidUser,
            amount: Number(bidAmount),
          }),
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Ошибка при ставке");
      }

      setSelectedAuction(data.auction);
      setSuccessMessage("Ставка успешно принята");
      setBidRecommendation(null);
      await loadAuctions();
      await loadProfile();
    } catch (err) {
      setBidError(err.message || "Не удалось сделать ставку");
    } finally {
      setBidLoading(false);
    }
  };

  const handleRecommendBid = async (e) => {
    e.preventDefault();
    if (!selectedAuction) return;

    try {
      setRecommendationLoading(true);
      setRecommendationError("");

      const response = await fetch(
        `http://127.0.0.1:8000/auctions/${selectedAuction.id}/bid-recommendation`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            user_value: Number(userValue),
          }),
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Ошибка расчета рекомендованной ставки");
      }

      setBidRecommendation(data);
      if (data.recommended_bid?.recommended_bid) {
        setBidAmount(Number(data.recommended_bid.recommended_bid).toFixed(2));
      }
    } catch (err) {
      setRecommendationError(err.message || "Не удалось рассчитать ставку");
    } finally {
      setRecommendationLoading(false);
    }
  };

  const handleMakeOffer = async (e) => {
    e.preventDefault();
    if (!selectedAuction) return;

    try {
      setOfferLoading(true);
      setOfferError("");
      setOfferResult(null);

      const response = await fetch(
        `http://127.0.0.1:8000/auctions/${selectedAuction.id}/offer`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            user: bidUser,
            amount: Number(offerAmount),
          }),
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Ошибка отправки оффера");
      }

      setOfferResult(data);
      setSelectedAuction(data.auction);
      await loadAuctions();
      await loadProfile();
    } catch (err) {
      setOfferError(err.message || "Не удалось отправить оффер");
    } finally {
      setOfferLoading(false);
    }
  };

  const handleOfferDecision = async (auctionId, offerId, action, counterAmount) => {
    try {
      setOfferLoading(true);
      setOfferError("");

      const response = await fetch(
        `http://127.0.0.1:8000/auctions/${auctionId}/offers/${offerId}/decision`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            action,
            counter_amount: counterAmount ? Number(counterAmount) : null,
          }),
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Ошибка решения по офферу");
      }

      setOfferResult(data);
      setSelectedAuction(data.auction);
      await loadAuctions();
      await loadProfile();
    } catch (err) {
      setOfferError(err.message || "Не удалось сохранить решение продавца");
    } finally {
      setOfferLoading(false);
    }
  };

  const handleFilterChange = (e) => {
    const { name, value } = e.target;
    setFilters((prev) => ({
      ...prev,
      [name]: value,
    }));
  };

  const filteredAuctions = useMemo(() => {
    return auctions.filter((auction) => {
      const brandMatch = filters.brand
        ? (auction.brand || "").toLowerCase().includes(filters.brand.toLowerCase())
        : true;

      const searchMatch = filters.search
        ? (auction.title || "").toLowerCase().includes(filters.search.toLowerCase())
        : true;

      const minMatch = filters.minPrice
        ? auction.current_price >= Number(filters.minPrice)
        : true;

      const maxMatch = filters.maxPrice
        ? auction.current_price <= Number(filters.maxPrice)
        : true;

      const categoryMatch = filters.category
        ? (auction.title || "").toLowerCase().includes(filters.category.toLowerCase()) ||
          (auction.brand || "").toLowerCase().includes(filters.category.toLowerCase())
        : true;

      return brandMatch && searchMatch && minMatch && maxMatch && categoryMatch;
    });
  }, [auctions, filters]);

  const handleSellTopLevelChange = (e) => {
    const { name, value } = e.target;
    setSellForm((prev) => ({
      ...prev,
      [name]: ["start_price", "bid_step_override"].includes(name)
        ? Number(value)
        : value,
    }));
  };

  const handleSellQuestionnaireChange = (e) => {
    const { name, value, type, checked } = e.target;
  
    setSellForm((prev) => {
      const updatedQuestionnaire = {
        ...prev.questionnaire,
        [name]:
          type === "checkbox"
            ? checked
            : name === "estimated_age"
            ? Number(value)
            : value,
      };
  
      if (name === "category") {
        updatedQuestionnaire.subcategory = "";
      }
  
      return {
        ...prev,
        questionnaire: updatedQuestionnaire,
      };
    });
  };

  const handleToggleColor = (color) => {
    setSellForm((prev) => {
      const currentColors = prev.questionnaire.colors || [];
      const hasColor = currentColors.includes(color);
  
      return {
        ...prev,
        questionnaire: {
          ...prev.questionnaire,
          colors: hasColor
            ? currentColors.filter((item) => item !== color)
            : [...currentColors, color],
        },
      };
    });
  };
  
  const handleCreateAuction = async () => {
    try {
      const response = await fetch("http://127.0.0.1:8000/auctions/", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(sellForm),
      });
  
      const data = await response.json();
  
      if (!response.ok) {
        throw new Error(data.detail || "Ошибка создания аукциона");
      }
  
      setSelectedAuction(data.auction);
      setPage("catalog");
      setCatalogView("product");
      await loadAuctions();
      await loadProfile();
      alert("Аукцион опубликован!");
  
    } catch (err) {
      alert("Ошибка: " + err.message);
    }
  };

  const handleImageUpload = async (fileList) => {
    const files = Array.from(fileList || []);
    if (!files.length) return;
  
    try {
      const uploadedImages = [];
  
      for (const file of files) {
        const formData = new FormData();
        formData.append("file", file);
  
        const response = await fetch("http://127.0.0.1:8000/auctions/upload-image", {
          method: "POST",
          body: formData,
        });
  
        const data = await response.json();
  
        if (!response.ok) {
          throw new Error(data.detail || "Ошибка загрузки изображения");
        }
  
        uploadedImages.push({
          url: data.image_url,
          name: file.name,
        });
      }
  
      setSellForm((prev) => ({
        ...prev,
        image_url: uploadedImages[0]?.url || "",
        image_urls: uploadedImages.map((img) => img.url),
      }));
  
      setSellImages(uploadedImages);
    } catch (err) {
      alert("Ошибка загрузки фото: " + err.message);
    }
  };

  const handleEstimateSell = async (e) => {
    e.preventDefault();
    setSellLoading(true);
    setSellError("");
    setSellResult(null);
  
    try {
      const response = await fetch("http://127.0.0.1:8000/pricing/estimate", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(sellForm),
      });
  
      const data = await response.json();
  
      if (!response.ok) {
        throw new Error(data.detail || JSON.stringify(data) || "Ошибка расчёта");
      }
      setSellResult(data);
      setSellForm((prev) => ({
        ...prev,
        start_price: data.recommended_start_price,
        bid_step_override: data.recommended_bid_step,
      }));
      
    } catch (err) {
      setSellError(`Не удалось рассчитать параметры товара: ${err.message}`);
    } finally {
      setSellLoading(false);
    }
  };

  const selectedCategory = categoryOptions.find(
    (item) => item.value === sellForm.questionnaire.category
  );
  
  const availableSubcategories = selectedCategory?.subcategories || [];

  const handleApplyPricingRecommendation = () => {
    if (!sellResult) return;
    setSellForm((prev) => ({
      ...prev,
      start_price: sellResult.recommended_start_price,
      bid_step_override: sellResult.recommended_bid_step,
    }));
  };

  return (
    <div className="page">
      <div className="container">
        <Header
          page={page}
          setPage={setPage}
          currentUserName={currentUserName}
          setCurrentUserName={setCurrentUserName}
        />

        {page === "catalog" && (
          catalogView === "grid" ? (
            <CatalogPage
              error={error}
              loading={loading}
              filters={filters}
              handleFilterChange={handleFilterChange}
              filteredAuctions={filteredAuctions}
              handleSelectAuction={handleSelectAuction}
            />
          ) : (
            <ProductPage
              selectedAuction={selectedAuction}
              bidError={bidError}
              successMessage={successMessage}
              bidUser={bidUser}
              setBidUser={setBidUser}
              bidAmount={bidAmount}
              setBidAmount={setBidAmount}
              handlePlaceBid={handlePlaceBid}
              bidLoading={bidLoading}
              userValue={userValue}
              setUserValue={setUserValue}
              handleRecommendBid={handleRecommendBid}
              recommendationLoading={recommendationLoading}
              recommendationError={recommendationError}
              bidRecommendation={bidRecommendation}
              offerAmount={offerAmount}
              setOfferAmount={setOfferAmount}
              handleMakeOffer={handleMakeOffer}
              offerLoading={offerLoading}
              offerError={offerError}
              offerResult={offerResult}
              handleOfferDecision={handleOfferDecision}
              onBack={() => setCatalogView("grid")}
            />
          )
        )}

        {page === "profile" && (
          <ProfilePage
            currentUserName={currentUserName}
            profileMode={profileMode}
            setProfileMode={setProfileMode}
            profileData={profileData}
            profileLoading={profileLoading}
            profileError={profileError}
            handleSelectAuction={handleOpenAuctionFromProfile}
            handleOfferDecision={handleOfferDecision}
            goToSell={() => setPage("sell")}
          />
        )}

        {page === "sell" && (
          <SellPage
            sellForm={sellForm}
            handleCreateAuction={handleCreateAuction}
            handleSellTopLevelChange={handleSellTopLevelChange}
            handleSellQuestionnaireChange={handleSellQuestionnaireChange}
            handleImageUpload={handleImageUpload}
            sellImages={sellImages}
            handleEstimateSell={handleEstimateSell}
            selectedCategory={selectedCategory}
            availableSubcategories={availableSubcategories}
            handleToggleColor={handleToggleColor}
            sellLoading={sellLoading}
            sellError={sellError}
            sellResult={sellResult}
            handleApplyPricingRecommendation={handleApplyPricingRecommendation}
          />
        )}
      </div>
    </div>
  );
}

export default App;
