const fs = require("fs");
const path = require("path");
const puppeteer = require("puppeteer-extra");
const StealthPlugin = require("puppeteer-extra-plugin-stealth");

puppeteer.use(StealthPlugin());

const ROOT = __dirname;
const DATA_DIR = path.join(ROOT, "data");
const SELL_FILE = path.join(DATA_DIR, "antam_sell.json");
const BUYBACK_FILE = path.join(DATA_DIR, "antam_buyback.json");
const SOURCE_PAGE = "https://www.logammulia.com/id";

function jakartaDate(timestamp) {
  const parts = new Intl.DateTimeFormat("en-CA", {
    timeZone: "Asia/Jakarta",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).formatToParts(new Date(Number(timestamp)));
  const value = Object.fromEntries(parts.map((part) => [part.type, part.value]));
  return `${value.year}-${value.month}-${value.day}`;
}

function loadJson(file) {
  if (!fs.existsSync(file)) return [];
  try {
    return JSON.parse(fs.readFileSync(file, "utf8"));
  } catch (error) {
    throw new Error(`Tidak dapat membaca ${path.basename(file)}: ${error.message}`);
  }
}

function normalize(records) {
  return records.filter(
    (record) =>
      Array.isArray(record) &&
      record.length === 2 &&
      Number.isFinite(Number(record[0])) &&
      Number.isFinite(Number(record[1]))
  );
}

function mergeHistory(existing, incoming) {
  const byDateAndPrice = new Map();
  for (const [timestamp, price] of normalize([...existing, ...incoming])) {
    const key = `${jakartaDate(timestamp)}-${Number(price)}`;
    byDateAndPrice.set(key, [Number(timestamp), Number(price)]);
  }
  return [...byDateAndPrice.values()].sort((a, b) => a[0] - b[0]);
}

async function fetchJsonInPage(page, url) {
  const response = await page.evaluate(async (targetUrl) => {
    const result = await fetch(targetUrl, {
      headers: { Accept: "application/json", "X-Requested-With": "XMLHttpRequest" },
      credentials: "include",
    });
    return { ok: result.ok, status: result.status, text: await result.text() };
  }, url);

  if (!response.ok) throw new Error(`Endpoint mengembalikan HTTP ${response.status}`);
  try {
    return JSON.parse(response.text);
  } catch {
    throw new Error(`Respons endpoint bukan JSON: ${response.text.slice(0, 160)}`);
  }
}

async function scrape() {
  fs.mkdirSync(DATA_DIR, { recursive: true });
  const browser = await puppeteer.launch({
    headless: true,
    args: ["--no-sandbox", "--disable-setuid-sandbox"],
  });

  try {
    const page = await browser.newPage();
    await page.setViewport({ width: 1365, height: 768 });
    await page.goto(SOURCE_PAGE, { waitUntil: "networkidle2", timeout: 120000 });

    if ((await page.url()).includes("captcha")) {
      throw new Error("Logam Mulia meminta verifikasi CAPTCHA. Coba jalankan kembali nanti.");
    }

    await page.waitForSelector('input[name="_token"]', { timeout: 30000 });
    const token = await page.$eval('input[name="_token"]', (element) => element.value);
    if (!token) throw new Error("CSRF token tidak ditemukan.");

    const sellUrl = `https://www.logammulia.com/data-base-price/gold_eai/sell?_token=${encodeURIComponent(token)}&transition=1`;
    const buybackUrl = `https://www.logammulia.com/data-base-price/gold/buy?_token=${encodeURIComponent(token)}`;
    const sellData = await fetchJsonInPage(page, sellUrl);
    const buybackData = await fetchJsonInPage(page, buybackUrl);

    const sellHistory = mergeHistory(loadJson(SELL_FILE), sellData);
    const buybackHistory = mergeHistory(loadJson(BUYBACK_FILE), buybackData);
    fs.writeFileSync(SELL_FILE, JSON.stringify(sellHistory, null, 2));
    fs.writeFileSync(BUYBACK_FILE, JSON.stringify(buybackHistory, null, 2));
    console.log(`Berhasil menyimpan ${sellHistory.length} harga jual dan ${buybackHistory.length} harga buyback.`);
  } finally {
    await browser.close();
  }
}

scrape().catch((error) => {
  console.error(`Scraper gagal: ${error.message}`);
  process.exitCode = 1;
});
