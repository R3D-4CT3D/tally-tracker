#!/usr/bin/env node
// Drives the real Tally auth flow against a running stack (see stack.sh) with
// Playwright. Requires the stack to already be up with a FRESH (unsetup)
// database -- run `stack.sh reset-db` first if setup has already run.
//
// Usage: node driver.mjs [screenshotDir] [baseUrl]
import { chromium } from "playwright";
import { mkdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const HERE = dirname(fileURLToPath(import.meta.url));
const SCREENSHOT_DIR = process.argv[2] ?? join(HERE, "screenshots");
const BASE_URL = process.argv[3] ?? "https://localhost";
mkdirSync(SCREENSHOT_DIR, { recursive: true });

const consoleErrors = [];
let failed = false;

const browser = await chromium.launch({ args: ["--no-sandbox", "--ignore-certificate-errors"] });
const context = await browser.newContext({ ignoreHTTPSErrors: true });
const page = await context.newPage();
page.on("console", (msg) => {
  if (msg.type() === "error") consoleErrors.push(msg.text());
});
page.on("pageerror", (err) => consoleErrors.push(`pageerror: ${err.message}`));

async function shot(name) {
  await page.screenshot({ path: join(SCREENSHOT_DIR, `${name}.png`), fullPage: true });
  console.log(`screenshot: ${name}.png`);
}

async function step(label, fn) {
  console.log(`--- ${label} ---`);
  try {
    await fn();
  } catch (err) {
    failed = true;
    console.error(`FAILED: ${label}`);
    console.error(err.message);
    await shot(`FAILED-${label.replace(/\W+/g, "-")}`);
  }
}

await step("setup wizard renders", async () => {
  await page.goto(BASE_URL + "/", { waitUntil: "networkidle" });
  await page.waitForSelector("text=Set up Tally", { timeout: 15000 });
  await shot("01-setup");
});

await step("submit setup form -> lands on /dashboard", async () => {
  await page.fill("#household_name", "The Doe Household");
  await page.fill("#owner_display_name", "Brandon");
  await page.fill("#owner_email", "brandon@example.com");
  await page.fill("#owner_password", "correcthorsebattery");
  await page.click('button:has-text("Create household")');
  await page.waitForSelector("text=Welcome, Brandon", { timeout: 15000 });
  if (!page.url().endsWith("/dashboard")) throw new Error(`unexpected URL: ${page.url()}`);
  await shot("02-dashboard-after-setup");
});

await step("logout -> lands on /login", async () => {
  await page.click('button:has-text("Log out")');
  await page.waitForSelector("text=Welcome back", { timeout: 15000 });
  if (!page.url().endsWith("/login")) throw new Error(`unexpected URL: ${page.url()}`);
  await shot("03-login-page");
});

await step("log back in -> lands on /dashboard again", async () => {
  await page.fill("#email", "brandon@example.com");
  await page.fill("#password", "correcthorsebattery");
  await page.click('button:has-text("Log in")');
  await page.waitForSelector("text=Welcome, Brandon", { timeout: 15000 });
  if (!page.url().endsWith("/dashboard")) throw new Error(`unexpected URL: ${page.url()}`);
  await shot("04-dashboard-after-login");
});

await browser.close();

console.log("\n=== CONSOLE ERRORS ===");
console.log(consoleErrors.length ? consoleErrors.join("\n") : "(none)");

if (failed) {
  console.error("\nDRIVER FAILED -- see FAILED-*.png screenshots and errors above");
  process.exit(1);
}
console.log("\nDRIVER OK");
