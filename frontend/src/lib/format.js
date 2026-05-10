export const fmtUSD = (n) => {
  if (n === null || n === undefined || isNaN(n)) return "—";
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(Number(n));
};

export const fmtUSDPrecise = (n) => {
  if (n === null || n === undefined || isNaN(n)) return "—";
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
  }).format(Number(n));
};

export const fmtNum = (n) => {
  if (n === null || n === undefined || isNaN(n)) return "—";
  return new Intl.NumberFormat("en-US").format(Number(n));
};

export const propertyTypeLabel = (t) => {
  const map = {
    residential: "Residential",
    commercial: "Commercial",
    land: "Land",
    manufactured_home: "Mfd. Home",
    mixed_use: "Mixed Use",
    unknown: "Unknown",
  };
  return map[t] || t || "Unknown";
};

export const taxStatusLabel = (s) => {
  const map = {
    delinquent: "Delinquent",
    in_foreclosure: "In Foreclosure",
    scheduled_for_sale: "Scheduled For Sale",
    struck_off: "Struck Off",
    paid: "Paid",
  };
  return map[s] || s || "—";
};
