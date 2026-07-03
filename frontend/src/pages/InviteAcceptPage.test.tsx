import { fireEvent, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { api } from "../lib/api";
import "../lib/i18n";
import { renderWithProviders } from "../test/renderWithProviders";
import { InviteAcceptPage } from "./InviteAcceptPage";

vi.mock("../lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../lib/api")>();
  return { ...actual, api: { get: vi.fn(), post: vi.fn() } };
});

describe("InviteAcceptPage", () => {
  it("shows an error and no form when the URL has no token", () => {
    renderWithProviders(<InviteAcceptPage />, { route: "/invite/accept" });

    expect(screen.getByRole("alert")).toHaveTextContent(/incomplete/);
    expect(screen.queryByLabelText("Email")).not.toBeInTheDocument();
  });

  it("submits the token from the URL plus the entered fields", async () => {
    vi.mocked(api.post).mockResolvedValue({ status: "ok" });
    vi.mocked(api.get).mockResolvedValue({
      user_id: "2",
      email: "gina@example.com",
      display_name: "Gina",
      role: "member",
      household_id: "h1",
      household_name: "House",
    });

    renderWithProviders(<InviteAcceptPage />, { route: "/invite/accept?token=abc123" });

    fireEvent.change(screen.getByLabelText("Your name"), { target: { value: "Gina" } });
    fireEvent.change(screen.getByLabelText("Email"), {
      target: { value: "gina@example.com" },
    });
    fireEvent.change(screen.getByLabelText("Password"), {
      target: { value: "correcthorsebattery" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Join household" }));

    await waitFor(() => {
      expect(api.post).toHaveBeenCalledWith("/invites/accept", {
        token: "abc123",
        email: "gina@example.com",
        display_name: "Gina",
        password: "correcthorsebattery",
      });
    });
  });
});
