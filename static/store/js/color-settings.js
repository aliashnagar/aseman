(() => {
  const toHex = (value) => {
    const color = value.trim();
    const hex = color.match(/^#([0-9a-f]{3}|[0-9a-f]{4}|[0-9a-f]{6}|[0-9a-f]{8})$/i);
    if (hex) {
      const digits = hex[1];
      if (digits.length <= 4) {
        return `#${digits.slice(0, 3).split("").map((digit) => digit + digit).join("")}`;
      }
      return `#${digits.slice(0, 6)}`;
    }

    const rgb = color.match(/^rgb\(\s*(\d{1,3})\s*,\s*(\d{1,3})\s*,\s*(\d{1,3})\s*\)$/i);
    if (!rgb) return null;

    const channels = rgb.slice(1).map(Number);
    if (channels.some((channel) => channel > 255)) return null;
    return `#${channels.map((channel) => channel.toString(16).padStart(2, "0")).join("")}`;
  };

  document.querySelectorAll("[data-color-picker-for]").forEach((picker) => {
    const colorInput = document.getElementById(picker.dataset.colorPickerFor);
    if (!(colorInput instanceof HTMLInputElement)) return;

    const syncPicker = () => {
      const hex = toHex(colorInput.value);
      if (hex) picker.value = hex;
    };

    syncPicker();
    colorInput.addEventListener("input", syncPicker);
    colorInput.addEventListener("change", syncPicker);
    picker.addEventListener("input", () => {
      colorInput.value = picker.value;
      colorInput.dispatchEvent(new Event("input", { bubbles: true }));
    });
  });
})();
