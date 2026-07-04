/**
 * Dollars-string <-> integer-cents conversions done entirely with string/int
 * arithmetic -- never `Number(dollars) * 100`, which reintroduces the float
 * rounding error the backend's integer-cents storage exists to avoid (e.g.
 * 19.99 * 100 === 1998.9999999999998 in IEEE 754).
 */

export function parseDollarsToCents(input: string): number {
  const trimmed = input.trim();
  const negative = trimmed.startsWith("-");
  const unsigned = trimmed.replace(/^[+-]/, "");
  const [wholePart, fractionPart = ""] = unsigned.split(".");
  const wholeCents = Number(wholePart || "0") * 100;
  const fractionCents = Number((fractionPart + "00").slice(0, 2));
  const cents = wholeCents + fractionCents;
  return negative ? -cents : cents;
}

export function formatCentsAsDollarsInput(cents: number): string {
  const negative = cents < 0;
  const abs = Math.abs(cents);
  const dollars = Math.floor(abs / 100);
  const remainder = String(abs % 100).padStart(2, "0");
  return `${negative ? "-" : ""}${dollars}.${remainder}`;
}

export function formatCentsDisplay(cents: number): string {
  const negative = cents < 0;
  const abs = Math.abs(cents);
  const dollars = Math.floor(abs / 100);
  const remainder = String(abs % 100).padStart(2, "0");
  return `${negative ? "-" : ""}$${dollars.toLocaleString()}.${remainder}`;
}
