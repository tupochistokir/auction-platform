import { useMemo, useState } from "react";

function SmartBrandInput({ value, onChange, options }) {
  const [isOpen, setIsOpen] = useState(false);

  const filteredOptions = useMemo(() => {
    if (!value) return options.slice(0, 8);
    return options
      .filter((item) => item.toLowerCase().includes(value.toLowerCase()))
      .slice(0, 8);
  }, [value, options]);

  const handleSelect = (brand) => {
    onChange({
      target: {
        name: "brand",
        value: brand,
        type: "text",
      },
    });
    setIsOpen(false);
  };

  return (
    <div className="smart-input-wrapper">
      <input
        name="brand"
        value={value}
        onChange={(e) => {
          onChange(e);
          setIsOpen(true);
        }}
        onFocus={() => setIsOpen(true)}
        placeholder="Начни вводить бренд"
      />

      {isOpen && filteredOptions.length > 0 && (
        <div className="smart-dropdown">
          {filteredOptions.map((brand) => (
            <button
              type="button"
              key={brand}
              className="smart-option"
              onClick={() => handleSelect(brand)}
            >
              {brand}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

export default SmartBrandInput;