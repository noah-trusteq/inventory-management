// Single source of truth for categorical chart colors (values are CSS tokens from App.vue)
// so a product category has the same color on every page.
const CATEGORY_COLORS = {
  "circuit boards": "var(--chart-1)",
  sensors: "var(--chart-2)",
  actuators: "var(--chart-3)",
  controllers: "var(--chart-4)",
  "power supplies": "var(--chart-5)",
};

export const getCategoryColor = (category) =>
  CATEGORY_COLORS[String(category || "").toLowerCase()] || "var(--chart-3)";
