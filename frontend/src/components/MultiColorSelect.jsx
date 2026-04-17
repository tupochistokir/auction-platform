function MultiColorSelect({ options, selectedColors, onToggleColor }) {
  return (
    <div className="multi-color-grid">
      {options.map((color) => {
        const isActive = selectedColors.includes(color);

        return (
          <button
            key={color}
            type="button"
            className={`color-chip ${isActive ? "active" : ""}`}
            onClick={() => onToggleColor(color)}
          >
            {color}
          </button>
        );
      })}
    </div>
  );
}

export default MultiColorSelect;