import { useCallback, useEffect, useMemo, useState } from "react";
import "./App.css";
import Header from "./components/Header";
import CatalogPage from "./pages/CatalogPage";
import SellPage from "./pages/SellPage";
import { categoryOptions } from "./data/categories";
import ProductPage from "./pages/ProductPage";
import ProfilePage from "./pages/ProfilePage";
import AuthPage from "./pages/AuthPage";
import FavoritesPage from "./pages/FavoritesPage";
import OffersPage from "./pages/OffersPage";

const API_URL = (import.meta.env.VITE_API_URL || "http://127.0.0.1:8000").replace(/\/$/, "");
const AUTH_TOKEN_KEY = "auction_auth_token";

const toDateTimeLocalValue = (date) => {
  const timezoneOffset = date.getTimezoneOffset() * 60000;
  return new Date(date.getTime() - timezoneOffset).toISOString().slice(0, 16);
};

const defaultAuctionEndTime = () => {
  const date = new Date();
  date.setDate(date.getDate() + 7);
  date.setHours(21, 0, 0, 0);
  return toDateTimeLocalValue(date);
};

const toNullableNumber = (value) => {
  if (value === "" || value === null || value === undefined) return null;
  const number = Number(value);
  return Number.isFinite(number) ? number : null;
};

const toOptionalIsoDate = (value) => {
  if (!value) return null;
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? null : date.toISOString();
};

const getApiErrorMessage = (data, fallback) => {
  const detail = data?.detail;

  if (typeof detail === "string") return detail;

  if (Array.isArray(detail)) {
    return detail
      .map((item) => {
        const path = Array.isArray(item.loc) ? item.loc.join(".") : "";
        return path ? `${path}: ${item.msg}` : item.msg;
      })
      .filter(Boolean)
      .join("; ");
  }

  if (detail && typeof detail === "object") {
    return JSON.stringify(detail);
  }

  return fallback;
};

const emptyAuthForm = {
  username: "",
  email: "",
  display_name: "",
  identifier: "",
  password: "",
};

function App() {
  const [page, setPage] = useState("catalog");
  const [catalogView, setCatalogView] = useState("grid");
  const [auctions, setAuctions] = useState([]);
  const [selectedAuction, setSelectedAuction] = useState(null);
  const [authToken, setAuthToken] = useState(() => localStorage.getItem(AUTH_TOKEN_KEY) || "");
  const [authUser, setAuthUser] = useState(null);
  const [authMode, setAuthMode] = useState("login");
  const [authForm, setAuthForm] = useState(emptyAuthForm);
  const [authLoading, setAuthLoading] = useState(false);
  const [authError, setAuthError] = useState("");
  const [profileMode, setProfileMode] = useState("buyer");
  const [profileData, setProfileData] = useState(null);
  const [profileLoading, setProfileLoading] = useState(false);
  const [profileError, setProfileError] = useState("");
  const [profileMessage, setProfileMessage] = useState("");
  const [favoritesData, setFavoritesData] = useState([]);
  const [favoritesLoading, setFavoritesLoading] = useState(false);
  const [favoritesError, setFavoritesError] = useState("");
  const [avatarLoading, setAvatarLoading] = useState(false);
  const [avatarError, setAvatarError] = useState("");

  const [filters, setFilters] = useState({
    brand: "",
    minPrice: "",
    maxPrice: "",
    search: "",
    category: "",
  });

  const [bidUser, setBidUser] = useState("");
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
    seller_name: "",
    start_price: 3000,
    bid_step_override: "",
    end_time: defaultAuctionEndTime(),
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

  const currentUserName = authUser?.display_name || authUser?.username || "";

  const buildLotPayload = useCallback(
    () => ({
      ...sellForm,
      seller_name: currentUserName,
      start_price: toNullableNumber(sellForm.start_price) || 0,
      bid_step_override: toNullableNumber(sellForm.bid_step_override),
      end_time: toOptionalIsoDate(sellForm.end_time),
      questionnaire: {
        ...sellForm.questionnaire,
        estimated_age: toNullableNumber(sellForm.questionnaire.estimated_age) || 0,
        has_tag: Boolean(sellForm.questionnaire.has_tag),
      },
    }),
    [currentUserName, sellForm]
  );

  useEffect(() => {
    if (!currentUserName) return;

    setBidUser(currentUserName);
    setSellForm((prev) => ({
      ...prev,
      seller_name: currentUserName,
    }));
  }, [currentUserName]);

  const loadAuthUser = useCallback(async () => {
    if (!authToken) {
      setAuthUser(null);
      return null;
    }

    try {
      const response = await fetch(`${API_URL}/auth/me`, {
        headers: {
          Authorization: `Bearer ${authToken}`,
        },
      });
      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Сессия недействительна");
      }

      setAuthUser(data.user);
      return data.user;
    } catch {
      localStorage.removeItem(AUTH_TOKEN_KEY);
      setAuthToken("");
      setAuthUser(null);
      setProfileData(null);
      setFavoritesData([]);
      return null;
    }
  }, [authToken]);

  const loadAuctions = useCallback(async () => {
    try {
      setLoading(true);
      setError("");

      const response = await fetch(`${API_URL}/auctions/`);
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

  const loadAuctionById = async (auctionId, sellerView = false) => {
    try {
      setBidError("");
      setSuccessMessage("");

      const response = await fetch(
        `${API_URL}/auctions/${auctionId}${sellerView ? "?seller_view=true" : ""}`,
        {
        headers: authToken ? { Authorization: `Bearer ${authToken}` } : {},
        }
      );
      if (!response.ok) {
        throw new Error("Ошибка загрузки аукциона");
      }

      const data = await response.json();
      setSelectedAuction(data);

      const minBid = Number(data.current_price || 0) + Number(data.recommended_bid_step || 0);
      setBidAmount(String(Math.round(minBid)));
      setUserValue(String(Math.round(Number(data.expected_final_price || minBid))));
      setOfferAmount(String(Math.round(Number(data.expected_final_price || minBid))));
      setBidRecommendation(null);
      setOfferResult(null);
    } catch {
      setBidError("Не удалось открыть аукцион");
    }
  };

  const loadProfile = useCallback(async () => {
    if (!authUser || !currentUserName.trim()) {
      setProfileData(null);
      setProfileError("");
      setProfileMessage("");
      setProfileLoading(false);
      return;
    }

    try {
      setProfileLoading(true);
      setProfileError("");

      const response = await fetch(
        `${API_URL}/auctions/profile/${encodeURIComponent(currentUserName)}`,
        {
          headers: {
            Authorization: `Bearer ${authToken}`,
          },
        }
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
  }, [authToken, authUser, currentUserName]);

  const loadFavorites = useCallback(async () => {
    if (!authUser || !authToken) {
      setFavoritesData([]);
      setFavoritesError("");
      setFavoritesLoading(false);
      return;
    }

    try {
      setFavoritesLoading(true);
      setFavoritesError("");

      const response = await fetch(`${API_URL}/auctions/favorites`, {
        headers: {
          Authorization: `Bearer ${authToken}`,
        },
      });
      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Ошибка загрузки избранного");
      }

      setFavoritesData(data.favorites || []);
    } catch (err) {
      setFavoritesError(err.message || "Не удалось загрузить избранное");
    } finally {
      setFavoritesLoading(false);
    }
  }, [authToken, authUser]);

  const requireAuth = (message) => {
    if (authUser) return true;

    setAuthMode("login");
    setAuthError(message);
    setPage("profile");
    return false;
  };

  useEffect(() => {
    loadAuthUser();
  }, [loadAuthUser]);

  useEffect(() => {
    loadAuctions();
  }, [loadAuctions]);

  useEffect(() => {
    if ((page === "profile" || page === "offers") && authUser) {
      loadProfile();
    }
  }, [page, authUser, loadProfile]);

  useEffect(() => {
    if (page === "favorites" && authUser) {
      loadFavorites();
    }
  }, [page, authUser, loadFavorites]);

  useEffect(() => {
    if (selectedAuction) {
      const minBid =
        Number(selectedAuction.current_price || 0) +
        Number(selectedAuction.recommended_bid_step || 0);
      setBidAmount(String(Math.round(minBid)));
      setUserValue(String(Math.round(Number(selectedAuction.expected_final_price || minBid))));
      setOfferAmount(String(Math.round(Number(selectedAuction.expected_final_price || minBid))));
      setRecommendationError("");
      setOfferError("");
    }
  }, [selectedAuction]);

  const handleAuthFormChange = (e) => {
    const { name, value } = e.target;
    setAuthForm((prev) => ({
      ...prev,
      [name]: value,
    }));
  };

  const handleAuthModeChange = (mode) => {
    setAuthMode(mode);
    setAuthError("");
  };

  const handleAuthSubmit = async (e) => {
    e.preventDefault();
    setAuthLoading(true);
    setAuthError("");

    const endpoint = authMode === "register" ? "register" : "login";
    const payload =
      authMode === "register"
        ? {
            username: authForm.username,
            email: authForm.email,
            password: authForm.password,
            display_name: authForm.display_name,
          }
        : {
            identifier: authForm.identifier,
            password: authForm.password,
          };

    try {
      const response = await fetch(`${API_URL}/auth/${endpoint}`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${authToken}`,
        },
        body: JSON.stringify(payload),
      });
      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Ошибка авторизации");
      }

      localStorage.setItem(AUTH_TOKEN_KEY, data.token);
      setAuthToken(data.token);
      setAuthUser(data.user);
      setAuthForm(emptyAuthForm);
      setProfileData(null);
      setFavoritesData([]);
      setProfileMode("buyer");
      setPage((currentPage) =>
        currentPage === "sell" || currentPage === "favorites" ? currentPage : "profile"
      );
    } catch (err) {
      setAuthError(err.message || "Не удалось войти в аккаунт");
    } finally {
      setAuthLoading(false);
    }
  };

  const handleLogout = async () => {
    try {
      await fetch(`${API_URL}/auth/logout`, { method: "POST" });
    } finally {
      localStorage.removeItem(AUTH_TOKEN_KEY);
      setAuthToken("");
      setAuthUser(null);
      setProfileData(null);
      setFavoritesData([]);
      setBidUser("");
      setPage("catalog");
    }
  };

  const handleSelectAuction = async (auction) => {
    await loadAuctionById(auction.id, false);
    setCatalogView("product");
  };

  const handleOpenAuctionFromProfile = async (auction) => {
    await loadAuctionById(auction.id, true);
    setCatalogView("product");
    setPage("catalog");
  };

  const handleOpenFavoriteAuction = async (auction) => {
    await loadAuctionById(auction.id, false);
    setCatalogView("product");
    setPage("catalog");
  };

  const handlePlaceBid = async (e) => {
    e.preventDefault();
    if (!selectedAuction) return;
    if (!requireAuth("Войдите или зарегистрируйтесь, чтобы делать ставки.")) return;

    try {
      setBidLoading(true);
      setBidError("");
      setSuccessMessage("");

      const response = await fetch(`${API_URL}/auctions/${selectedAuction.id}/bid`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${authToken}`,
        },
        body: JSON.stringify({
          user: currentUserName,
          amount: Number(bidAmount),
        }),
      });

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
    if (!requireAuth("Войдите или зарегистрируйтесь, чтобы получить персональную рекомендацию.")) return;

    try {
      setRecommendationLoading(true);
      setRecommendationError("");

      const response = await fetch(
        `${API_URL}/auctions/${selectedAuction.id}/bid-recommendation`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${authToken}`,
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
        setBidAmount(String(Math.round(Number(data.recommended_bid.recommended_bid))));
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
    if (!requireAuth("Войдите или зарегистрируйтесь, чтобы отправить оффер продавцу.")) return;

    try {
      setOfferLoading(true);
      setOfferError("");
      setOfferResult(null);

      const response = await fetch(`${API_URL}/auctions/${selectedAuction.id}/offer`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${authToken}`,
        },
        body: JSON.stringify({
          user: currentUserName,
          amount: Number(offerAmount),
        }),
      });

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
    if (!requireAuth("Войдите в кабинет продавца, чтобы ответить на оффер.")) return;

    try {
      setOfferLoading(true);
      setOfferError("");

      const response = await fetch(
        `${API_URL}/auctions/${auctionId}/offers/${offerId}/decision`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${authToken}`,
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

  const handleBuyerOfferDecision = async (auctionId, offerId, action) => {
    if (!requireAuth("Войдите в аккаунт, чтобы ответить на встречную цену продавца.")) return null;

    try {
      setOfferLoading(true);
      setOfferError("");

      const response = await fetch(
        `${API_URL}/auctions/${auctionId}/offers/${offerId}/buyer-decision`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${authToken}`,
          },
          body: JSON.stringify({ action }),
        }
      );
      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Не удалось ответить на встречную цену");
      }

      setOfferResult(data);
      if (selectedAuction?.id === auctionId) {
        setSelectedAuction(data.auction);
      }
      await loadAuctions();
      await loadProfile();
      return data;
    } catch (err) {
      setOfferError(err.message || "Не удалось ответить на встречную цену");
      throw err;
    } finally {
      setOfferLoading(false);
    }
  };

  const handleLotSignal = async (signal) => {
    if (!selectedAuction) return;
    if (!requireAuth("Войдите в аккаунт, чтобы сохранять реакции на лоты.")) return;

    try {
      const response = await fetch(`${API_URL}/auctions/${selectedAuction.id}/${signal}`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${authToken}`,
        },
      });
      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Не удалось обновить реакцию на лот");
      }

      setSelectedAuction(data.auction);
      if (signal === "favorite") {
        const updatedAuction = data.auction;
        const isFavorite = Boolean(updatedAuction?.viewer_signals?.favorited);
        setFavoritesData((prev) => {
          const withoutCurrent = prev.filter(
            (item) => item.auction?.id !== updatedAuction.id
          );
          return isFavorite
            ? [{ auction: updatedAuction, favorited_at: new Date().toISOString() }, ...withoutCurrent]
            : withoutCurrent;
        });
      }
      await loadAuctions();
      await loadProfile();
      if (signal === "favorite") {
        await loadFavorites();
      }
    } catch (err) {
      setBidError(err.message || "Не удалось обновить реакцию на лот");
    }
  };

  const handleUpdateAuction = async (auctionId, patch) => {
    if (!requireAuth("Войдите в кабинет продавца, чтобы редактировать лот.")) return null;

    try {
      setProfileError("");

      const response = await fetch(`${API_URL}/auctions/${auctionId}`, {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${authToken}`,
        },
        body: JSON.stringify(patch),
      });
      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Не удалось обновить лот");
      }

      if (selectedAuction?.id === auctionId) {
        setSelectedAuction(data.auction);
      }
      await loadAuctions();
      await loadProfile();
      return data;
    } catch (err) {
      setProfileError(err.message || "Не удалось обновить лот");
      throw err;
    }
  };

  const uploadAuctionImages = async (fileList) => {
    const files = Array.from(fileList || []);
    if (!files.length) return [];

    const uploadedUrls = [];
    for (const file of files) {
      const formData = new FormData();
      formData.append("file", file);

      const response = await fetch(`${API_URL}/auctions/upload-image`, {
        method: "POST",
        body: formData,
      });
      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Ошибка загрузки изображения");
      }

      uploadedUrls.push(data.image_url);
    }
    return uploadedUrls;
  };

  const handleUploadAuctionImages = async (auction, fileList) => {
    if (!requireAuth("Войдите в кабинет продавца, чтобы добавить фото к лоту.")) return null;

    const uploadedUrls = await uploadAuctionImages(fileList);
    if (!uploadedUrls.length) return null;

    const existingUrls = Array.isArray(auction.image_urls)
      ? auction.image_urls.filter(Boolean)
      : auction.image_url
      ? [auction.image_url]
      : [];
    const imageUrls = [...existingUrls, ...uploadedUrls];
    return handleUpdateAuction(auction.id, {
      image_url: imageUrls[0],
      image_urls: imageUrls,
    });
  };

  const handleAcceptBid = async (auctionId, bidId) => {
    if (!requireAuth("Войдите в кабинет продавца, чтобы принять ставку.")) return null;

    try {
      setProfileError("");

      const response = await fetch(`${API_URL}/auctions/${auctionId}/bids/${bidId}/accept`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${authToken}`,
        },
      });
      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Не удалось принять ставку");
      }

      if (selectedAuction?.id === auctionId) {
        setSelectedAuction(data.auction);
      }
      await loadAuctions();
      await loadProfile();
      return data;
    } catch (err) {
      setProfileError(err.message || "Не удалось принять ставку");
      throw err;
    }
  };

  const handleProfileUpdate = async (patch) => {
    if (!requireAuth("Войдите в аккаунт, чтобы редактировать профиль.")) return null;

    try {
      setProfileError("");
      setProfileMessage("");

      const response = await fetch(`${API_URL}/auth/me`, {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${authToken}`,
        },
        body: JSON.stringify(patch),
      });
      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Не удалось обновить профиль");
      }

      setAuthUser(data.user);
      setProfileMessage("Профиль сохранён");
      setProfileData((prev) =>
        prev
          ? {
              ...prev,
              user: {
                ...prev.user,
                id: data.user.id,
                username: data.user.username,
                name: data.user.display_name || data.user.username,
                email: data.user.email,
                phone: data.user.phone,
                age: data.user.age,
                city: data.user.city,
                bio: data.user.bio,
                is_incognito: data.user.is_incognito,
                avatar_url: data.user.avatar_url,
              },
            }
          : prev
      );
      return data;
    } catch (err) {
      setProfileError(err.message || "Не удалось обновить профиль");
      throw err;
    }
  };

  const handleFilterChange = (e) => {
    const { name, value } = e.target;
    setFilters((prev) => ({
      ...prev,
      [name]: value,
    }));
  };

  const handleCategorySelect = (category) => {
    setFilters((prev) => ({
      ...prev,
      category,
    }));
    setCatalogView("grid");
  };

  const filteredAuctions = useMemo(() => {
    return auctions.filter((auction) => {
      const searchMatch = filters.search
        ? [
            auction.title,
            auction.brand,
            auction.description,
            auction.questionnaire?.category,
            auction.questionnaire?.subcategory,
          ]
            .filter(Boolean)
            .join(" ")
            .toLowerCase()
            .includes(filters.search.toLowerCase())
        : true;

      const minMatch = filters.minPrice
        ? auction.current_price >= Number(filters.minPrice)
        : true;

      const maxMatch = filters.maxPrice
        ? auction.current_price <= Number(filters.maxPrice)
        : true;

      const auctionCategory = (auction.questionnaire?.category || "").toLowerCase();
      const auctionSubcategory = (auction.questionnaire?.subcategory || "").toLowerCase();
      const selectedCategory = filters.category.toLowerCase();
      const selectedCategoryOption = categoryOptions.find(
        (category) => category.value === filters.category
      );
      const selectedChildCategories =
        selectedCategoryOption?.subcategories?.map((item) => item.value.toLowerCase()) || [];
      const categoryMatch = filters.category
        ? auctionCategory === selectedCategory ||
          auctionSubcategory === selectedCategory ||
          selectedChildCategories.includes(auctionCategory) ||
          selectedChildCategories.includes(auctionSubcategory)
        : true;

      return searchMatch && minMatch && maxMatch && categoryMatch;
    });
  }, [auctions, filters]);

  const handleSellTopLevelChange = (e) => {
    const { name, value } = e.target;
    setSellForm((prev) => ({
      ...prev,
      [name]:
        name === "start_price"
          ? Number(value)
          : name === "bid_step_override"
          ? value === ""
            ? ""
            : Number(value)
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
    if (!requireAuth("Войдите или зарегистрируйтесь, чтобы опубликовать товар.")) return;

    try {
      const response = await fetch(`${API_URL}/auctions/`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${authToken}`,
        },
        body: JSON.stringify(buildLotPayload()),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(getApiErrorMessage(data, "Ошибка создания аукциона"));
      }

      setSelectedAuction(data.auction);
      setPage("catalog");
      setCatalogView("product");
      await loadAuctions();
      await loadProfile();
      alert("Аукцион опубликован");
    } catch (err) {
      alert("Ошибка: " + err.message);
    }
  };

  const handleImageUpload = async (fileList) => {
    const files = Array.from(fileList || []);
    if (!files.length) return;
    if (!requireAuth("Войдите или зарегистрируйтесь, чтобы загрузить фото товара.")) return;

    try {
      const uploadedImages = [];

      for (const file of files) {
        const formData = new FormData();
        formData.append("file", file);

        const response = await fetch(`${API_URL}/auctions/upload-image`, {
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

  const handleAvatarUpload = async (fileList) => {
    const file = Array.from(fileList || [])[0];
    if (!file) return;
    if (!requireAuth("Войдите в аккаунт, чтобы обновить аватар.")) return;

    try {
      setAvatarLoading(true);
      setAvatarError("");

      const formData = new FormData();
      formData.append("file", file);

      const response = await fetch(`${API_URL}/auth/avatar`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${authToken}`,
        },
        body: formData,
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Ошибка загрузки аватара");
      }

      setAuthUser(data.user);
      setProfileData((prev) =>
        prev
          ? {
              ...prev,
              user: {
                ...prev.user,
                avatar_url: data.avatar_url,
              },
            }
          : prev
      );
    } catch (err) {
      setAvatarError(err.message || "Не удалось загрузить аватар");
    } finally {
      setAvatarLoading(false);
    }
  };

  const handleEstimateSell = async (e) => {
    e.preventDefault();
    if (!requireAuth("Войдите или зарегистрируйтесь, чтобы рассчитать параметры товара.")) return;

    setSellLoading(true);
    setSellError("");
    setSellResult(null);

    try {
      const response = await fetch(`${API_URL}/pricing/estimate`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(buildLotPayload()),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(getApiErrorMessage(data, "Ошибка расчёта"));
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

  const handleApplyPricingRecommendation = () => {
    if (!sellResult) return;
    setSellForm((prev) => ({
      ...prev,
      start_price: sellResult.recommended_start_price,
      bid_step_override: sellResult.recommended_bid_step,
    }));
  };

  const goToCatalog = () => {
    setAuthError("");
    setPage("catalog");
    setCatalogView("grid");
  };

  const goToSell = () => {
    setAuthError("");
    setPage("sell");
  };

  const goToProfile = () => {
    setAuthError("");
    setPage("profile");
  };

  const goToFavorites = () => {
    setAuthError("");
    setPage("favorites");
  };

  const goToOffers = () => {
    setAuthError("");
    setPage("offers");
  };

  const renderAuthGate = (variant) => (
    <AuthPage
      mode={authMode}
      setMode={handleAuthModeChange}
      form={authForm}
      onChange={handleAuthFormChange}
      onSubmit={handleAuthSubmit}
      loading={authLoading}
      error={authError}
      variant={variant}
    />
  );

  return (
    <div className="page">
      <div className="container">
        <Header
          page={page}
          goToCatalog={goToCatalog}
          goToSell={goToSell}
          goToProfile={goToProfile}
          goToFavorites={goToFavorites}
          authUser={authUser}
          currentUserName={currentUserName}
          avatarUrl={authUser?.avatar_url}
          onLogout={handleLogout}
        />

        {page === "catalog" && (
          catalogView === "grid" ? (
            <CatalogPage
              error={error}
              loading={loading}
              filters={filters}
              handleFilterChange={handleFilterChange}
              handleCategorySelect={handleCategorySelect}
              filteredAuctions={filteredAuctions}
              handleSelectAuction={handleSelectAuction}
            />
          ) : (
            <ProductPage
              selectedAuction={selectedAuction}
              bidError={bidError}
              successMessage={successMessage}
              bidUser={bidUser}
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
              handleLotSignal={handleLotSignal}
              onBack={() => setCatalogView("grid")}
            />
          )
        )}

        {page === "profile" && (
          authUser ? (
            <ProfilePage
              currentUserName={currentUserName}
              profileMode={profileMode}
              setProfileMode={setProfileMode}
              profileData={profileData}
              profileLoading={profileLoading}
              profileError={profileError}
              profileMessage={profileMessage}
              avatarUrl={authUser?.avatar_url}
              avatarLoading={avatarLoading}
              avatarError={avatarError}
              handleAvatarUpload={handleAvatarUpload}
              handleProfileUpdate={handleProfileUpdate}
              handleSelectAuction={handleOpenAuctionFromProfile}
              handleOfferDecision={handleOfferDecision}
              handleBuyerOfferDecision={handleBuyerOfferDecision}
              handleUpdateAuction={handleUpdateAuction}
              handleUploadAuctionImages={handleUploadAuctionImages}
              handleAcceptBid={handleAcceptBid}
              goToSell={() => setPage("sell")}
              goToOffers={goToOffers}
            />
          ) : (
            renderAuthGate("profile")
          )
        )}

        {page === "offers" && (
          authUser ? (
            <OffersPage
              profileData={profileData}
              profileLoading={profileLoading}
              profileError={profileError}
              handleSelectAuction={handleOpenAuctionFromProfile}
              handleOfferDecision={handleOfferDecision}
              handleBuyerOfferDecision={handleBuyerOfferDecision}
              goToProfile={goToProfile}
            />
          ) : (
            renderAuthGate("profile")
          )
        )}

        {page === "favorites" && (
          authUser ? (
            <FavoritesPage
              favorites={favoritesData}
              loading={favoritesLoading}
              error={favoritesError}
              handleSelectAuction={handleOpenFavoriteAuction}
              goToCatalog={goToCatalog}
            />
          ) : (
            renderAuthGate("favorites")
          )
        )}

        {page === "sell" && (
          authUser ? (
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
          ) : (
            renderAuthGate("sell")
          )
        )}
      </div>
    </div>
  );
}

export default App;
