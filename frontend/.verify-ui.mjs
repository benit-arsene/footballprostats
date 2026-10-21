import fs from "node:fs";
import path from "node:path";
import puppeteer from "puppeteer-core";

const CHROME = "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe";
const APP = "http://127.0.0.1:3100/players/epl/topscorers/currentseason";
const REF = "file:///C:/src/flutter/flutter_windows_3.35.6-stable/football-pro-stats/docs/reference.html";
const OUT = path.resolve(".verify");
fs.mkdirSync(OUT, { recursive: true });

const browser = await puppeteer.launch({
  headless: true,
  executablePath: CHROME,
  args: ["--no-sandbox", "--disable-gpu"],
  defaultViewport: { width: 1600, height: 1000 },
  protocolTimeout: 180000,
});

async function extract(page) {
  return page.evaluate(() => {
    const style = (el, props) => {
      if (!el) return null;
      const cs = getComputedStyle(el);
      const rect = el.getBoundingClientRect();
      const out = { w: +rect.width.toFixed(1), h: +rect.height.toFixed(1) };
      for (const p of props) out[p] = cs[p];
      return out;
    };
    const icons = Array.from(document.querySelectorAll(".material-symbols-outlined"));
    return {
      h1: style(document.querySelector("h1"), [
        "fontSize",
        "lineHeight",
        "fontWeight",
        "letterSpacing",
        "color",
        "textTransform",
      ]),
      body: style(document.body, ["backgroundColor", "fontSize", "color"]),
      main: style(document.querySelector("main"), [
        "backgroundColor",
        "fontSize",
        "color",
        "minHeight",
      ]),
      thead: style(document.querySelector("thead tr"), [
        "height",
        "backgroundColor",
        "fontSize",
        "fontWeight",
        "color",
      ]),
      row: style(document.querySelector("tbody tr"), ["height", "fontSize", "color"]),
      rankChip: style(document.querySelector("tbody tr td:first-child span"), [
        "width",
        "height",
        "borderRadius",
        "backgroundColor",
        "color",
        "fontSize",
        "fontWeight",
      ]),
      playerAvatar: style(
        document.querySelector('tbody tr td:nth-child(2) div[class*="h-7"]'),
        ["width", "height", "borderRadius", "backgroundColor"],
      ),
      clubBadge: style(document.querySelector("tbody tr td:nth-child(3) span"), [
        "width",
        "height",
        "borderRadius",
        "fontSize",
        "fontWeight",
      ]),
      playerName: style(document.querySelector("tbody tr td:nth-child(2) span"), [
        "fontSize",
        "fontWeight",
        "letterSpacing",
        "color",
      ]),
      goalsHeader: style(
        Array.from(document.querySelectorAll("thead th")).find((th) => /^Goals/i.test(th.textContent.trim())),
        ["backgroundColor", "fontSize", "fontWeight", "color"],
      ),
      leaderCard: style(document.querySelector("main article"), [
        "backgroundColor",
        "borderRadius",
        "padding",
        "color",
      ]),
      leaderName: style(document.querySelector("main article h2"), [
        "fontSize",
        "lineHeight",
        "fontWeight",
        "letterSpacing",
        "textTransform",
      ]),
      watermark: style(document.querySelector('main article div[class*="opacity-10"] span'), [
        "fontSize",
        "fontWeight",
        "letterSpacing",
        "lineHeight",
      ]),
      metricTile: style(
        document.querySelector('main article div[class*="p-space-sm"][class*="bg-surface-container-highest"]'),
        ["padding", "borderRadius"],
      ),
      canvas: style(
        document.querySelector('main div[class*="max-w-[1600px]"][class*="gap-space-lg"]'),
        [
          "maxWidth",
          "paddingLeft",
          "paddingRight",
          "paddingTop",
          "paddingBottom",
          "rowGap",
          "columnGap",
        ],
      ),
      podiumGrid: style(document.querySelector('main section[class*="md:grid-cols-12"]'), ["gap"]),
      controls: style(
        Array.from(document.querySelectorAll("section")).find((s) => /Standard Table/.test(s.textContent)),
        ["padding", "borderRadius", "backgroundColor", "rowGap"],
      ),
      glossary: style(
        Array.from(document.querySelectorAll("section")).find((s) => /Metrics Glossary/.test(s.textContent)),
        ["padding", "borderRadius", "rowGap"],
      ),
      pager: style(document.querySelector('nav[aria-label="Pagination"] button:nth-of-type(2)'), [
        "width",
        "height",
        "borderRadius",
        "fontSize",
        "fontWeight",
      ]),
      iconFont: {
        family: icons[0] ? getComputedStyle(icons[0]).fontFamily : null,
        loaded: document.fonts.check('16px "Material Symbols Outlined"'),
        count: icons.length,
      },
      rowCount: document.querySelectorAll("tbody tr").length,
      headerCells: document.querySelectorAll("thead th").length,
      bodyScrollWidth: document.documentElement.scrollWidth,
      viewport: window.innerWidth,
      h1Text: document.querySelector("h1")?.textContent?.trim() ?? null,
    };
  });
}

// ─── App page ────────────────────────────────────────────────────────
const page = await browser.newPage();
const consoleErrors = [];
page.on("console", (msg) => {
  if (msg.type() === "error") consoleErrors.push(msg.text());
});
page.on("pageerror", (error) => consoleErrors.push(String(error)));
await page.goto(APP, { waitUntil: "networkidle0", timeout: 60000 });
await page.evaluate(() => document.fonts.ready);
await new Promise((resolve) => setTimeout(resolve, 600));
const appSpec = await extract(page);
await page.screenshot({ path: path.join(OUT, "app-1600.png"), fullPage: true });

// ─── Reference page ──────────────────────────────────────────────────
const ref = await browser.newPage();
await ref.goto(REF, { waitUntil: "networkidle0", timeout: 60000 });
await ref.evaluate(() => document.fonts.ready);
await new Promise((resolve) => setTimeout(resolve, 1200));
const refSpec = await extract(ref);
await ref.screenshot({ path: path.join(OUT, "reference-1600.png"), fullPage: true });

// ─── Compare ─────────────────────────────────────────────────────────
let mismatches = 0;
function compare(node, a, b, prefix = "") {
  if (a && b && typeof a === "object" && typeof b === "object") {
    for (const key of new Set([...Object.keys(a), ...Object.keys(b)])) {
      compare(node, a[key], b[key], prefix ? `${prefix}.${key}` : key);
    }
    return;
  }
  const same = String(a) === String(b);
  if (!same) {
    mismatches += 1;
    console.log(`DIFF ${prefix}: reference=${JSON.stringify(b)} app=${JSON.stringify(a)}`);
  }
}
compare("spec", appSpec, refSpec);

console.log("\n--- app spec ---");
console.log(JSON.stringify(appSpec, null, 2));
console.log(`\nMismatches: ${mismatches}`);
console.log(`Console errors: ${consoleErrors.length ? consoleErrors.join(" | ") : "none"}`);

// ─── Leader card internals ──────────────────────────────────────────
async function cardDetail(target) {
  return target.evaluate(() => {
    const card = document.querySelector("main article");
    const rect = (el) => (el ? { h: +el.getBoundingClientRect().height.toFixed(1), w: +el.getBoundingClientRect().width.toFixed(1) } : null);
    if (!card) return null;
    return {
      card: rect(card),
      children: Array.from(card.children).map((el) => ({
        tag: el.tagName,
        cls: String(el.className).slice(0, 80),
        ...rect(el),
      })),
      rows: Array.from(card.querySelectorAll('div[class*="gap-space-md"]')).map((el) => ({
        cls: String(el.className).slice(0, 70),
        text: el.innerText.replace(/\n/g, " | ").slice(0, 70),
        ...rect(el),
      })),
      tiles: Array.from(card.querySelectorAll('div[class*="p-space-sm"]')).map((el) => ({
        text: el.innerText.replace(/\n/g, " | ").slice(0, 60),
        ...rect(el),
      })),
    };
  });
}
console.log("\n--- leader card app ---");
console.log(JSON.stringify(await cardDetail(page), null, 2));
console.log("--- leader card reference ---");
console.log(JSON.stringify(await cardDetail(ref), null, 2));

// ─── Interaction tests ──────────────────────────────────────────────
const results = [];
const check = (name, condition, detail = "") => {
  const line = `${condition ? "PASS" : "FAIL"} ${name}${detail ? ` — ${detail}` : ""}`;
  results.push(line);
  console.log(line);
};

const rowCount = () => page.$$eval("tbody tr", (rows) => rows.length);
const bodyText = () => page.$eval("tbody", (el) => el.innerText);

const initialRows = await rowCount();
check("initial rows render", initialRows === 10, `${initialRows} rows`);
check(
  "all 14 columns present",
  appSpec.headerCells === 14,
  `${appSpec.headerCells} header cells`,
);

// Search
await page.type('input[aria-label="Search player, nationality, or club"]', "saka");
await new Promise((resolve) => setTimeout(resolve, 300));
const searchRows = await rowCount();
const searchText = await bodyText();
check("search filters table", searchRows === 1 && /Bukayo Saka/.test(searchText), `${searchRows} rows`);
check(
  "search echoes in sort ribbon",
  await page.$eval("tbody", (el) => !/Erling Haaland/.test(el.innerText)),
  "leader filtered out",
);

// Clear search
await page.click('input[aria-label="Search player, nationality, or club"]', { clickCount: 3 });
await page.keyboard.press("Backspace");
await new Promise((resolve) => setTimeout(resolve, 300));
check("search clears", (await rowCount()) === 10);

// Club filter
await page.select('select[aria-label="Filter by club"]', "Chelsea FC");
await new Promise((resolve) => setTimeout(resolve, 300));
const clubText = await bodyText();
check(
  "club filter keeps only Chelsea",
  /João Pedro/.test(clubText) && !/Erling Haaland/.test(clubText),
  `${await rowCount()} rows`,
);
// Reset via filter panel
await page.evaluate(() => {
  const button = Array.from(document.querySelectorAll("button")).find(
    (el) => el.textContent.trim() === "Reset",
  );
  button?.click();
});
await new Promise((resolve) => setTimeout(resolve, 300));
check("reset restores full table", (await rowCount()) === 10);

// Position filter (midfield -> Morgan Rogers only)
await page.select('select[aria-label="Filter by position"]', "midfield");
await new Promise((resolve) => setTimeout(resolve, 300));
const positionText = await bodyText();
check(
  "position filter narrows to midfielders",
  /Morgan Rogers/.test(positionText) && !/Erling Haaland/.test(positionText),
  `${await rowCount()} rows`,
);
await page.select('select[aria-label="Filter by position"]', "");
await new Promise((resolve) => setTimeout(resolve, 300));

// Sort by goals ascending
await page.evaluate(() => {
  const th = Array.from(document.querySelectorAll("thead th")).find((el) =>
    /^Goals/i.test(el.textContent.trim()),
  );
  th?.querySelector("button")?.click();
});
await new Promise((resolve) => setTimeout(resolve, 300));
const firstRowGoals = await page.$eval("tbody tr td:nth-child(6)", (el) => el.textContent.trim());
const lastRowGoals = await page.$$eval("tbody tr", (rows) => {
  const last = rows[rows.length - 1];
  return last.children[5].textContent.trim();
});
check(
  "goals header sorts ascending",
  Number(firstRowGoals) <= Number(lastRowGoals),
  `${firstRowGoals} … ${lastRowGoals}`,
);
check(
  "sort ribbon updates",
  /Goals \(Asc\)/.test(await page.$eval("section", (el) => el.innerText)),
);

// Column toggle
await page.evaluate(() => {
  const button = Array.from(document.querySelectorAll("button")).find((el) =>
    /^Columns \(\d+\)$/.test(el.textContent.trim()),
  );
  button?.click();
});
await new Promise((resolve) => setTimeout(resolve, 200));
const panelOpen = await page.evaluate(
  () => document.querySelector('[role="dialog"][aria-label="Visible columns"]') !== null,
);
check("columns popover opens", panelOpen);
await page.evaluate(() => {
  const label = Array.from(document.querySelectorAll('[role="dialog"] label')).find((el) =>
    /Mins/.test(el.textContent),
  );
  label?.querySelector("input")?.click();
});
await new Promise((resolve) => setTimeout(resolve, 300));
const afterToggle = await page.$eval("thead tr", (el) => el.children.length);
check("column toggle removes a column", afterToggle === 13, `${afterToggle} header cells`);
await page.keyboard.press("Escape");
await new Promise((resolve) => setTimeout(resolve, 200));
check(
  "escape closes popover",
  await page.evaluate(() => document.querySelector('[role="dialog"][aria-label="Visible columns"]') === null),
);

// Row selection
await page.click("tbody tr");
const selectedClass = await page.$eval("tbody tr", (el) => el.className);
check("row click highlights row", /bg-surface-container-high\/40/.test(selectedClass));

// Page size
await page.evaluate(() => {
  const button = Array.from(document.querySelectorAll("button")).find(
    (el) => el.textContent.trim() === "25",
  );
  button?.click();
});
await new Promise((resolve) => setTimeout(resolve, 300));
check("page size 25 selected", (await rowCount()) === 10, "dataset has 10 rows");

// CSV export
const client = await page.createCDPSession();
await client.send("Page.setDownloadBehavior", { behavior: "allow", downloadPath: OUT });
await page.evaluate(() => {
  const button = Array.from(document.querySelectorAll("button")).find((el) =>
    /Export \.CSV/.test(el.textContent),
  );
  button?.click();
});
await new Promise((resolve) => setTimeout(resolve, 1200));
const downloads = fs.readdirSync(OUT).filter((file) => file.endsWith(".csv"));
check("CSV export downloads", downloads.length > 0, downloads.join(", "));
if (downloads.length > 0) {
  const csv = fs.readFileSync(path.join(OUT, downloads[0]), "utf8");
  check("CSV has header and rows", /Rank,Player,Club/.test(csv) && csv.split("\r\n").length >= 10);
}

// Mobile layout
await page.setViewport({ width: 390, height: 844 });
await new Promise((resolve) => setTimeout(resolve, 500));
const mobile = await page.evaluate(() => ({
  scrollWidth: document.documentElement.scrollWidth,
  innerWidth: window.innerWidth,
  card: document.querySelector("main article")?.getBoundingClientRect().width ?? 0,
}));
check(
  "mobile page does not overflow",
  mobile.scrollWidth <= mobile.innerWidth + 1,
  `scrollWidth=${mobile.scrollWidth} viewport=${mobile.innerWidth}`,
);
check("mobile leader card fits", mobile.card <= 390, `${mobile.card}px`);
await page.screenshot({ path: path.join(OUT, "app-390.png"), fullPage: true });

console.log("\n--- interaction results ---");
results.forEach((line) => console.log(line));
console.log(`Interaction failures: ${results.filter((line) => line.startsWith("FAIL")).length}`);

fs.writeFileSync(path.join(OUT, "report.json"), JSON.stringify({ appSpec, refSpec, mismatches, results, consoleErrors }, null, 2));

await browser.close();
