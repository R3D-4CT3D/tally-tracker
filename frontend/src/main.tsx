import React from "react";
import ReactDOM from "react-dom/client";
import { QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter } from "react-router-dom";

// Self-hosted fonts (not a runtime Google Fonts call) -- same-origin, PWA
// cacheable, no third-party DNS/TLS on first paint. Only the weights/axes
// actually used are imported: Fraunces' "standard" (non-soft, non-wonk)
// variable axis for display headings/numbers, Inter's 400/500/600/700
// static weights for body text.
import "@fontsource-variable/fraunces/standard.css";
import "@fontsource/inter/latin-400.css";
import "@fontsource/inter/latin-500.css";
import "@fontsource/inter/latin-600.css";
import "@fontsource/inter/latin-700.css";

import App from "./App";
import "./lib/i18n";
import "./index.css";
import { queryClient } from "./lib/queryClient";
import { ThemeProvider } from "./design-system/ThemeProvider";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <ThemeProvider>
      <QueryClientProvider client={queryClient}>
        <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
          <App />
        </BrowserRouter>
      </QueryClientProvider>
    </ThemeProvider>
  </React.StrictMode>,
);
