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
  const r = box(runner);
  // content height = sum of children heights + gaps (excluding stretch)
  const inner = runner.children[0];
  const contentH = [...inner.children].reduce((a, el) => a + el.getBoundingClientRect().height, 0);
  return {
    section: box(section),
    leader: box(arts[0]),
    runner: r,
    runnerInnerContentH: Math.round(contentH),
    leaderText: arts[0].innerText.replace(/\n+/g, "|").slice(0, 60),
    runnerText: runner.innerText.replace(/\n+/g, "|").slice(0, 120),
  };
});
console.log(JSON.stringify(out));
await browser.close();
