const colorClassMap = {
  "Чёрный": "black",
  "Белый": "white",
  "Коричневый": "brown",
  "Бежевый": "beige",
  "Серый": "gray",
  "Синий": "blue",
  "Голубой": "sky",
  "Красный": "red",
  "Зелёный": "green",
  "Хаки": "khaki",
  "Фиолетовый": "purple",
  "Оранжевый": "orange",
};

function MultiColorSelect({ options, selectedColors, onToggleColor }) {
  return (
    <div className="multi-color-grid">
      {options.map((color) => {
        const isActive = selectedColors.includes(color);
        const colorClass = colorClassMap[color] || "default";

        return (
          <button
            key={color}
            type="button"
            className={`color-chip color-${colorClass} ${isActive ? "active" : ""}`}
            onClick={() => onToggleColor(color)}
          >
            <span className="color-swatch" aria-hidden="true" />
            <span>{color}</span>
          </button>
        );
      })}
    </div>
  );
}

export default MultiColorSelect;
