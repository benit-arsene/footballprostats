import puppeteer from "puppeteer-core";
const CHROME = "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe";
const browser = await puppeteer.launch({ headless: true, executablePath: CHROME, args: ["--no-sandbox","--disable-gpu"], defaultViewport: { width: 1600, height: 1200 }, protocolTimeout: 180000 });
const page = await browser.newPage();
await page.goto("http://localhost:3000/players/epl/topscorers/currentseason", { waitUntil: "networkidle2", timeout: 180000 });
await page.waitForSelector("main article", { timeout: 60000 });
const out = await page.evaluate(() => {
  const box = (el) => { const r = el.getBoundingClientRect(); return { w: Math.round(r.width), h: Math.round(r.height) }; };
  const section = document.querySelector("main section.md\\:grid-cols-12");
  const arts = [...document.querySelectorAll("main article")];
  const runner = arts[1];
  const inner = runner.children[0];
  const kids = [...inner.children].map((el, i) => ({
    i, tag: el.tagName, ...box(el), text: el.innerText.replace(/\n+/g, " | ").slice(0, 44),
  }));
  // overflow / wrap detection inside the card
  const overflowing = [];
  for (const el of runner.querySelectorAll("*")) {
    if (el.scrollWidth > el.clientWidth + 1) overflowing.push({ cls: String(el.className).slice(0, 46), tag: el.tagName, scrollW: el.scrollWidth, clientW: el.clientWidth });
  }
  const pillars = inner.querySelectorAll("div.grid")[0];
  const pboxes = [...pillars.children].map(el => ({ ...box(el), text: el.innerText.replace(/\n+/g, "|").slice(0,40) }));
  const tiles = [...runner.querySelectorAll("div.grid")][1];
  const tboxes = [...tiles.children].map(el => ({ ...box(el), text: el.innerText.replace(/\n+/g, "|").slice(0,40) }));
  return {
    section: box(section),
    leader: box(arts[0]),
    runner: box(runner),
    runnerKids: kids,
    pillars: pboxes,
    tiles: tboxes,
    overflowing,
  };
});
console.log(JSON.stringify(out, null, 1));
await browser.close();
