import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import App from "./App";
import "./lib/i18n";

describe("App", () => {
  it("renders the app title", () => {
    render(<App />);
    expect(screen.getByText("Tally")).toBeInTheDocument();
  });
});
