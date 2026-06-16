export const AI_COMPARISON_FIELDS = [
  ["brand", "Бренд"],
  ["category", "Категория"],
  ["subcategory", "Подкатегория"],
  ["condition", "Состояние"],
  ["material", "Материал"],
  ["estimated_age", "Возраст"],
  ["has_tag", "Бирка"],
  ["colors", "Цвета"],
  ["style", "Стиль"],
  ["defects", "Дефекты"],
];

export const AI_PROOF_HINTS = {
  brand: "логотип, бирка бренда или фирменная фурнитура крупным планом",
  category: "вещь целиком на ровной поверхности или на человеке",
  subcategory: "силуэт и конструкция вещи полностью",
  condition: "зоны износа: воротник, манжеты, подошва, фурнитура",
  material: "состав на внутренней бирке или фактура ткани крупным планом",
  estimated_age: "бирка, год выпуска, артикул или характерные винтажные детали",
  has_tag: "оригинальная бирка, ярлык или место, где бирка отсутствует",
  colors: "фото при дневном свете без фильтров",
  style: "вещь целиком, чтобы был виден крой и посадка",
  defects: "каждый дефект отдельным крупным кадром",
};

const VALUE_LABELS = {
  category: {
    outerwear: "верхняя одежда",
    tops: "верх",
    bottoms: "низ",
    shoes: "обувь",
    accessories: "аксессуары",
    dresses: "платья",
  },
  subcategory: {
    bomber: "бомбер",
    leather_jacket: "кожаная куртка",
    denim_jacket: "джинсовая куртка",
    windbreaker: "ветровка",
    puffer: "пуховик",
    sheepskin: "дублёнка",
    coat: "пальто",
    trench: "тренч",
    hoodie: "худи / свитшот",
    tshirt: "футболка",
    shirt: "рубашка / лонгслив",
    sweater: "свитер",
    longsleeve: "лонгслив",
    jeans: "джинсы",
    pants: "брюки",
    shorts: "шорты",
    skirt: "юбка",
    dress: "платье",
    sneakers: "кроссовки",
    boots: "ботинки",
    loafers: "лоферы",
    bag: "сумка",
    cap: "кепка",
    belt: "ремень",
    scarf: "шарф",
  },
  condition: {
    excellent: "отличное",
    good: "хорошее",
    normal: "нормальное",
    bad: "с дефектами",
  },
};

const MISSING_VALUES = new Set([
  "",
  "unknown",
  "other",
  "not specified",
  "no name",
  "generic",
  "none",
  "no defects",
  "—",
]);

export const formatVerificationValue = (field, value) => {
  if (value === null || value === undefined || value === "") return "—";
  if (Array.isArray(value)) {
    const formatted = value
      .map((item) => formatVerificationValue(field, item))
      .filter((item) => item && item !== "—");
    return formatted.length ? formatted.join(", ") : "—";
  }
  if (typeof value === "boolean") return value ? "да" : "нет";
  if (field === "estimated_age") {
    const age = Number(value);
    return Number.isFinite(age) && age > 0 ? `${age} лет` : "—";
  }

  const normalized = String(value).trim();
  return VALUE_LABELS[field]?.[normalized] || normalized;
};

export const normalizeCompareValue = (value) => {
  if (Array.isArray(value)) {
    return value
      .map((item) => String(item ?? "").trim().toLowerCase())
      .filter(Boolean)
      .sort()
      .join(",");
  }

  return String(value ?? "").trim().toLowerCase();
};

export const isEmptyCompareValue = (value) => {
  if (Array.isArray(value)) return value.length === 0;
  return MISSING_VALUES.has(normalizeCompareValue(value));
};

export const valuesLookEqual = (left, right) => {
  if (Array.isArray(left) || Array.isArray(right)) {
    const leftValues = Array.isArray(left) ? left : [left];
    const rightValues = Array.isArray(right) ? right : [right];
    const leftSet = new Set(leftValues.map(normalizeCompareValue).filter(Boolean));

    return rightValues
      .map(normalizeCompareValue)
      .filter(Boolean)
      .some((item) => leftSet.has(item));
  }

  return normalizeCompareValue(left) === normalizeCompareValue(right);
};

const getVerificationStatus = (sellerValue, aiValue, confidence) => {
  const sellerMissing = isEmptyCompareValue(sellerValue);
  const aiMissing = isEmptyCompareValue(aiValue);
  const matches = !sellerMissing && !aiMissing && valuesLookEqual(sellerValue, aiValue);

  if (matches && confidence >= 0.6) {
    return {
      type: "verified",
      tone: "ok",
      marker: "✓",
      title: "сверено",
      explanation: "анкета и фото совпали",
      needsProof: false,
    };
  }

  if (sellerMissing && !aiMissing && confidence >= 0.6) {
    return {
      type: "suggestion",
      tone: "warn",
      marker: "?",
      title: "AI предлагает заполнить",
      explanation: "в анкете поле пустое, на фото признак виден",
      needsProof: false,
    };
  }

  if (!sellerMissing && !aiMissing && !matches && confidence >= 0.85) {
    return {
      type: "conflict",
      tone: "danger",
      marker: "!",
      title: "нужно уточнить",
      explanation: "AI уверен, что на фото другое значение",
      needsProof: true,
    };
  }

  if (!sellerMissing && !aiMissing && !matches && confidence >= 0.6) {
    return {
      type: "uncertain",
      tone: "warn",
      marker: "?",
      title: "есть сомнение",
      explanation: "AI видит отличие, но уверенность не максимальная",
      needsProof: true,
    };
  }

  if (aiMissing || confidence < 0.45) {
    return {
      type: "missing_ai",
      tone: "warn",
      marker: "?",
      title: "нужно доп. фото",
      explanation: "по текущим фото признак не подтверждён",
      needsProof: true,
    };
  }

  return {
    type: "low_confidence",
    tone: "warn",
    marker: "?",
    title: "оставлено значение анкеты",
    explanation: "AI не набрал достаточную уверенность для вывода",
    needsProof: true,
  };
};

export const buildAiVerificationRows = (aiFields = {}, questionnaireSnapshot = {}) =>
  AI_COMPARISON_FIELDS.map(([field, label]) => {
    const item = aiFields[field] || {};
    const aiValue = item.value;
    const sellerValue = questionnaireSnapshot[field];
    const confidence = Number(item.confidence || 0);

    const status = getVerificationStatus(sellerValue, aiValue, confidence);

    return {
      field,
      label,
      sellerValue,
      aiValue,
      confidence,
      status,
      proofHint: AI_PROOF_HINTS[field],
    };
  });

export const buildRowsFromVerificationReport = (report = {}) => {
  const rows = Array.isArray(report.fields) ? report.fields : [];
  return rows.map((row) => {
    const status = row.status || getVerificationStatus(row.seller_value, row.ai_value, Number(row.confidence || 0));
    return {
      field: row.field,
      label: row.label,
      sellerValue: row.seller_value,
      aiValue: row.ai_value,
      confidence: Number(row.confidence || 0),
      status,
      proofHint: row.proof_hint || AI_PROOF_HINTS[row.field],
    };
  });
};

export const buildVerificationSummary = (rows = []) => {
  const verified = rows.filter((row) => row.status?.type === "verified").length;
  const conflicts = rows.filter((row) => row.status?.type === "conflict").length;
  const warnings = rows.filter(
    (row) =>
      row.status?.type === "uncertain" ||
      row.status?.type === "missing_ai" ||
      row.status?.type === "low_confidence" ||
      row.status?.type === "suggestion"
  ).length;

  if (!rows.length) {
    return {
      level: "empty",
      verified,
      conflicts,
      warnings,
      reviewRequired: false,
      title: "AI-сверка не проводилась",
      description: "для паспорта проверки нужно загрузить фото и запустить анализ",
    };
  }

  if (conflicts > 0) {
    return {
      level: "danger",
      verified,
      conflicts,
      warnings,
      reviewRequired: true,
      title: "Есть характеристики, которые нужно уточнить",
      description: "по части признаков AI увереннее видит другое значение; лот попадёт на ручную проверку",
    };
  }

  if (warnings > 0) {
    return {
      level: "warn",
      verified,
      conflicts,
      warnings,
      reviewRequired: false,
      title: "Основные признаки проверены, но есть сомнения",
      description: "для спорных полей лучше добавить отдельное подтверждающее фото",
    };
  }

  return {
    level: "ok",
    verified,
    conflicts,
    warnings,
    reviewRequired: false,
    title: "Характеристики сверены с фото",
    description: "анкета продавца совпала с AI-анализом по проверенным признакам",
  };
};
