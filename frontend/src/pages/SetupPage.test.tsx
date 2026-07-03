import { fireEvent, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { api } from "../lib/api";
import "../lib/i18n";
import { renderWithProviders } from "../test/renderWithProviders";
import { SetupPage } from "./SetupPage";

vi.mock("../lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../lib/api")>();
  return { ...actual, api: { get: vi.fn(), post: vi.fn() } };
});

describe("SetupPage", () => {
  it("renders the required fields and submits them to POST /setup", async () => {
    vi.mocked(api.post).mockResolvedValue({ status: "ok" });
    vi.mocked(api.get).mockResolvedValue({
      user_id: "1",
      email: "jamie@example.com",
      display_name: "Jamie",
      role: "owner",
      household_id: "h1",
      household_name: "The Doe Household",
    });

    renderWithProviders(<SetupPage />);

    fireEvent.change(screen.getByLabelText("Household name"), {
      target: { value: "The Doe Household" },
    });
    fireEvent.change(screen.getByLabelText("Your name"), { target: { value: "Jamie" } });
    fireEvent.change(screen.getByLabelText("Email"), {
      target: { value: "jamie@example.com" },
    });
    fireEvent.change(screen.getByLabelText("Password"), {
      target: { value: "correcthorsebattery" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Create household" }));

    await waitFor(() => {
      expect(api.post).toHaveBeenCalledWith("/setup", {
        household_name: "The Doe Household",
        owner_display_name: "Jamie",
        owner_email: "jamie@example.com",
        owner_password: "correcthorsebattery",
      });
    });
  });

  it("shows the backend's error message on failure", async () => {
    const { ApiError } = await import("../lib/api");
    vi.mocked(api.post).mockRejectedValue(new ApiError(409, "Setup has already been completed"));

    renderWithProviders(<SetupPage />);

    fireEvent.change(screen.getByLabelText("Household name"), { target: { value: "X" } });
    fireEvent.change(screen.getByLabelText("Your name"), { target: { value: "X" } });
    fireEvent.change(screen.getByLabelText("Email"), { target: { value: "x@example.com" } });
    fireEvent.change(screen.getByLabelText("Password"), { target: { value: "correcthorsebattery" } });
    fireEvent.click(screen.getByRole("button", { name: "Create household" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Setup has already been completed",
    );
  });
});
