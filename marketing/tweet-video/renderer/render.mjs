// render.mjs — captures deterministic frames of scene.html via Playwright
// Emits PNGs to ./frames/, then ffmpeg stitches them into out/video-silent.mp4
import { chromium } from "playwright";
import { spawn } from "node:child_process";
import { promises as fs } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(__dirname, "..");
const FRAMES_DIR = path.join(__dirname, "frames");
const OUT_DIR = path.join(ROOT, "out");
const OUT_MP4 = path.join(OUT_DIR, "video-silent.mp4");
const SCENE_URL = "file://" + path.join(__dirname, "scene.html");

const FPS = 30;
const DURATION = 15.0;
const WIDTH = 1080;
const HEIGHT = 1080;
const TOTAL_FRAMES = Math.round(DURATION * FPS);

async function main() {
  await fs.mkdir(FRAMES_DIR, { recursive: true });
  await fs.mkdir(OUT_DIR, { recursive: true });

  // Clean old frames
  for (const f of await fs.readdir(FRAMES_DIR)) {
    if (f.endsWith(".png")) await fs.unlink(path.join(FRAMES_DIR, f));
  }

  console.log(`[render] ${TOTAL_FRAMES} frames @ ${FPS}fps -> ${FRAMES_DIR}`);
  const t0 = Date.now();
  const browser = await chromium.launch({
    headless: true,
    args: ["--force-device-scale-factor=1"],
  });
  const context = await browser.newContext({
    viewport: { width: WIDTH, height: HEIGHT },
    deviceScaleFactor: 1,
    colorScheme: "dark",
  });
  const page = await context.newPage();
  await page.goto(SCENE_URL, { waitUntil: "networkidle" });

  for (let f = 0; f < TOTAL_FRAMES; f++) {
    const t = f / FPS;
    await page.evaluate((tt) => window.renderAt(tt), t);
    const out = path.join(FRAMES_DIR, `frame_${String(f).padStart(5, "0")}.png`);
    await page.screenshot({ path: out, type: "png", omitBackground: false });
    if (f % 30 === 0 || f === TOTAL_FRAMES - 1) {
      process.stdout.write(`  frame ${f + 1}/${TOTAL_FRAMES} (t=${t.toFixed(2)}s)\n`);
    }
  }

  await browser.close();
  const rt = ((Date.now() - t0) / 1000).toFixed(1);
  console.log(`[render] captured in ${rt}s`);

  // Stitch with ffmpeg
  console.log(`[render] ffmpeg stitching to ${OUT_MP4}`);
  await new Promise((resolve, reject) => {
    const ff = spawn(
      "ffmpeg",
      [
        "-y",
        "-hide_banner",
        "-loglevel", "warning",
        "-framerate", String(FPS),
        "-i", path.join(FRAMES_DIR, "frame_%05d.png"),
        "-c:v", "libx264",
        "-preset", "slow",
        "-crf", "18",
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        "-r", String(FPS),
        OUT_MP4,
      ],
      { stdio: "inherit" }
    );
    ff.on("close", (code) =>
      code === 0 ? resolve() : reject(new Error(`ffmpeg exited ${code}`))
    );
  });
  console.log(`[render] done -> ${OUT_MP4}`);
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
