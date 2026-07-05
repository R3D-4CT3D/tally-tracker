// Flash-of-wrong-theme fix: runs before any stylesheet/module script, so the
// `dark` class is already correct on first paint -- React mounting and
// src/design-system/ThemeProvider.tsx's effect run too late to avoid a
// one-frame flash otherwise. A same-origin static file (not an inline
// <script> block) so it satisfies the app's `script-src 'self'` CSP
// (deploy/Caddyfile) without needing a nonce or a hash allowlist entry.
// Must stay in sync with ThemeProvider's own precedence (localStorage, then
// matchMedia) -- same key name, same fallback order.
(function () {
  var stored = window.localStorage.getItem("tally-theme");
  var dark =
    stored === "dark" ||
    (stored !== "light" && window.matchMedia("(prefers-color-scheme: dark)").matches);
  if (dark) document.documentElement.classList.add("dark");
})();
