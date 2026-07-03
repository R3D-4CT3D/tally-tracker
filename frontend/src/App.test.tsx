import { screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import App from "./App";
import { ApiError, api } from "./lib/api";
import "./lib/i18n";
import { renderWithProviders } from "./test/renderWithProviders";

vi.mock("./lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("./lib/api")>();
  return { ...actual, api: { get: vi.fn(), post: vi.fn() } };
});

describe("App routing", () => {
  it("redirects to /setup when setup is not complete", async () => {
    vi.mocked(api.get).mockImplementation((path: string) => {
      if (path === "/setup/status") return Promise.resolve({ is_setup: false });
      return Promise.reject(new Error("unexpected path: " + path));
    });

    renderWithProviders(<App />, { route: "/" });

    expect(await screen.findByText("Set up Tally")).toBeInTheDocument();
  });

  it("redirects to /login when setup is complete but not authenticated", async () => {
    vi.mocked(api.get).mockImplementation((path: string) => {
      if (path === "/setup/status") return Promise.resolve({ is_setup: true });
      if (path === "/auth/me") return Promise.reject(new ApiError(401, "Not authenticated"));
      return Promise.reject(new Error("unexpected path: " + path));
    });

    renderWithProviders(<App />, { route: "/" });

    expect(await screen.findByText("Welcome back")).toBeInTheDocument();
  });

  it("redirects to /dashboard when authenticated", async () => {
    vi.mocked(api.get).mockImplementation((path: string) => {
      if (path === "/setup/status") return Promise.resolve({ is_setup: true });
      if (path === "/auth/me") {
        return Promise.resolve({
          user_id: "1",
          email: "ada@example.com",
          display_name: "Ada",
          role: "owner",
          household_id: "h1",
          household_name: "The Test House",
        });
      }
      return Promise.reject(new Error("unexpected path: " + path));
    });

    renderWithProviders(<App />, { route: "/" });

    expect(await screen.findByText("Welcome, Ada")).toBeInTheDocument();
    expect(screen.getByText("The Test House")).toBeInTheDocument();
  });
});
