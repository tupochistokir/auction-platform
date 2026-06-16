export const secondStores = [
  {
    id: "vintage-rail",
    name: "Vintage Rail",
    district: "Москва, центр",
    address: "адрес будет добавлен после подключения партнера",
    concept: "брендовая верхняя одежда, трикотаж и винтажные аксессуары",
    dropSchedule: "пилотные дропы по понедельникам",
    auctionFormat: "лучшие позиции выходят короткими аукционами",
    mapUrl: "https://yandex.ru/maps/?text=%D1%81%D0%B5%D0%BA%D0%BE%D0%BD%D0%B4-%D1%85%D0%B5%D0%BD%D0%B4%20%D0%9C%D0%BE%D1%81%D0%BA%D0%B2%D0%B0%20%D1%86%D0%B5%D0%BD%D1%82%D1%80",
    sellerAliases: ["vintage rail", "vintagerail"],
  },
  {
    id: "archive-mix",
    name: "Archive Mix",
    district: "Москва, север",
    address: "адрес будет добавлен после подключения партнера",
    concept: "редкие худи, джинсы, куртки и спортивные бренды",
    dropSchedule: "подборка новых лотов два раза в неделю",
    auctionFormat: "эксклюзивные вещи идут через ставки, базовые остаются в каталоге",
    mapUrl: "https://yandex.ru/maps/?text=%D1%81%D0%B5%D0%BA%D0%BE%D0%BD%D0%B4-%D1%85%D0%B5%D0%BD%D0%B4%20%D0%9C%D0%BE%D1%81%D0%BA%D0%B2%D0%B0%20%D1%81%D0%B5%D0%B2%D0%B5%D1%80",
    sellerAliases: ["archive mix", "archivemix"],
  },
  {
    id: "local-drop",
    name: "Local Drop",
    district: "Москва, юго-запад",
    address: "адрес будет добавлен после подключения партнера",
    concept: "капсульные подборки после завоза и проверенные вещи с бирками",
    dropSchedule: "короткие продажи в день завоза",
    auctionFormat: "товары открываются партиями, покупает тот, кто предложил больше",
    mapUrl: "https://yandex.ru/maps/?text=%D1%81%D0%B5%D0%BA%D0%BE%D0%BD%D0%B4-%D1%85%D0%B5%D0%BD%D0%B4%20%D0%9C%D0%BE%D1%81%D0%BA%D0%B2%D0%B0%20%D1%8E%D0%B3%D0%BE-%D0%B7%D0%B0%D0%BF%D0%B0%D0%B4",
    sellerAliases: ["local drop", "localdrop"],
  },
];

const normalize = (value) => String(value || "").trim().toLowerCase();

export const getAuctionSecondStoreId = (auction) => {
  const questionnaire = auction?.questionnaire || {};
  const analysis = auction?.analysis || {};

  return normalize(
    auction?.second_store_id ||
      questionnaire.second_store_id ||
      questionnaire.store_id ||
      questionnaire.partner_store_id ||
      analysis.second_store_id
  );
};

export const findSecondStoreForAuction = (auction) => {
  const explicitStoreId = getAuctionSecondStoreId(auction);
  const sellerName = normalize(
    auction?.seller_name || auction?.seller_public_profile?.display_name
  );

  return (
    secondStores.find((store) => {
      if (explicitStoreId && explicitStoreId === store.id) return true;
      return store.sellerAliases.some((alias) => sellerName.includes(alias));
    }) || null
  );
};

export const isSecondStoreAuction = (auction) => Boolean(findSecondStoreForAuction(auction));
