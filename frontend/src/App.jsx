import { useEffect, useMemo, useState } from "react";
import "./App.css";
import Header from "./components/Header";
import CatalogPage from "./pages/CatalogPage";
import SellPage from "./pages/SellPage";
import { categoryOptions } from "./data/categories";
import ProductPage from "./pages/ProductPage";

function App() {
  const [page, setPage] = useState("catalog");
  const [catalogView, setCatalogView] = useState("grid");
  const [auctions, setAuctions] = useState([]);
  const [selectedAuction, setSelectedAuction] = useState(null);

  const [filters, setFilters] = useState({
    brand: "",
    minPrice: "",
    maxPrice: "",
    search: "",
    category: "",
  });

  const [bidUser, setBidUser] = useState("Кирилл");
  const [bidAmount, setBidAmount] = useState("");

  const [loading, setLoading] = useState(false);
  const [bidLoading, setBidLoading] = useState(false);
  const [error, setError] = useState("");
  const [bidError, setBidError] = useState("");
  const [successMessage, setSuccessMessage] = useState("");

  const [sellForm, setSellForm] = useState({
    title: "",
    start_price: 3000,
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

  const loadAuctions = async () => {
    try {
      setLoading(true);
      setError("");

      const response = await fetch("http://127.0.0.1:8000/auctions/");
      if (!response.ok) {
        throw new Error("Ошибка загрузки аукционов");
      }

      const data = await response.json();
      setAuctions(data.auctions);

      if (!selectedAuction && data.auctions.length > 0) {
        setSelectedAuction(data.auctions[0]);
      } else if (selectedAuction) {
        const updated = data.auctions.find((a) => a.id === selectedAuction.id);
        if (updated) {
          setSelectedAuction(updated);
        }
      }
    } catch (err) {
      setError("Не удалось загрузить аукционы. Проверь, запущен ли backend.");
    } finally {
      setLoading(false);
    }
  };

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

      const minBid = data.current_price + data.recommended_bid_step;
      setBidAmount(minBid.toFixed(2));
    } catch (err) {
      setBidError("Не удалось открыть аукцион");
    }
  };

  useEffect(() => {
    loadAuctions();
  }, []);

  useEffect(() => {
    if (selectedAuction) {
      const minBid = selectedAuction.current_price + selectedAuction.recommended_bid_step;
      setBidAmount(minBid.toFixed(2));
    }
  }, [selectedAuction]);

  const handleSelectAuction = async (auction) => {
    await loadAuctionById(auction.id);
    setCatalogView("product");
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
      await loadAuctions();
    } catch (err) {
      setBidError(err.message || "Не удалось сделать ставку");
    } finally {
      setBidLoading(false);
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
        ? auction.brand.toLowerCase().includes(filters.brand.toLowerCase())
        : true;

      const searchMatch = filters.search
        ? auction.title.toLowerCase().includes(filters.search.toLowerCase())
        : true;

      const minMatch = filters.minPrice
        ? auction.current_price >= Number(filters.minPrice)
        : true;

      const maxMatch = filters.maxPrice
        ? auction.current_price <= Number(filters.maxPrice)
        : true;

      const categoryMatch = filters.category
        ? auction.title.toLowerCase().includes(filters.category.toLowerCase()) ||
          auction.brand.toLowerCase().includes(filters.category.toLowerCase())
        : true;

      return brandMatch && searchMatch && minMatch && maxMatch && categoryMatch;
    });
  }, [auctions, filters]);

  const handleSellTopLevelChange = (e) => {
    const { name, value } = e.target;
    setSellForm((prev) => ({
      ...prev,
      [name]: name === "start_price" ? Number(value) : value,
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
        throw new Error("Ошибка создания аукциона");
      }
  
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

  return (
    <div className="page">
      <div className="container">
        <Header page={page} setPage={setPage} />

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
              onBack={() => setCatalogView("grid")}
            />
          )
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
          />
        )}
      </div>
    </div>
  );
}

export default App;