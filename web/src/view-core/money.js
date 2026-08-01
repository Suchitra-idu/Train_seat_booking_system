// L0 view-core: money + distance formatting. Pure - given data, returns a string.
// The API sends money as integer minor units ({ cents, currency }); LKR renders as "Rs".

const CURRENCY_PREFIX = { LKR: "Rs" };

/**
 * @param {{cents: number, currency?: string}} money
 * @returns {string} e.g. "Rs 1,234.50"
 */
export function formatMoney(money) {
  if (!money || typeof money.cents !== "number" || Number.isNaN(money.cents)) {
    return "-";
  }
  const currency = money.currency || "LKR";
  const prefix = CURRENCY_PREFIX[currency] || currency;
  const negative = money.cents < 0;
  const abs = Math.abs(money.cents);
  const major = Math.floor(abs / 100);
  const minor = String(abs % 100).padStart(2, "0");
  const grouped = major.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",");
  return `${negative ? "-" : ""}${prefix} ${grouped}.${minor}`;
}

/**
 * @param {number} km
 * @returns {string} e.g. "116 km"
 */
export function formatKm(km) {
  if (typeof km !== "number" || Number.isNaN(km)) return "-";
  const rounded = Math.round(km * 10) / 10;
  return `${Number.isInteger(rounded) ? rounded : rounded.toFixed(1)} km`;
}
