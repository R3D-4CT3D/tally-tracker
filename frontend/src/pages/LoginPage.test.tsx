import { fireEvent, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { api } from "../lib/api";
import "../lib/i18n";
import { renderWithProviders } from "../test/renderWithProviders";
import { LoginPage } from "./LoginPage";

vi.mock("../lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../lib/api")>();
  return { ...actual, api: { get: vi.fn(), post: vi.fn() } };
});

describe("LoginPage", () => {
  it("submits email and password to POST /auth/login", async () => {
    vi.mocked(api.post).mockResolvedValue({ status: "ok" });
    vi.mocked(api.get).mockResolvedValue({
      user_id: "1",
      email: "brandon@example.com",
      display_name: "Brandon",
      role: "owner",
      household_id: "h1",
      household_name: "House",
    });

    renderWithProviders(<LoginPage />);

    fireEvent.change(screen.getByLabelText("Email"), {
      target: { value: "brandon@example.com" },
    });
    fireEvent.change(screen.getByLabelText("Password"), {
      target: { value: "correcthorsebattery" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Log in" }));

    await waitFor(() => {
      expect(api.post).toHaveBeenCalledWith("/auth/login", {
        email: "brandon@example.com",
        password: "correcthorsebattery",
      });
    });
  });

  it("shows a generic message on invalid credentials", async () => {
    const { ApiError } = await import("../lib/api");
    vi.mocked(api.post).mockRejectedValue(new ApiError(401, "Invalid email or password"));

    renderWithProviders(<LoginPage />);

    fireEvent.change(screen.getByLabelText("Email"), { target: { value: "x@example.com" } });
    fireEvent.change(screen.getByLabelText("Password"), { target: { value: "wrong" } });
    fireEvent.click(screen.getByRole("button", { name: "Log in" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Invalid email or password");
  });
});
