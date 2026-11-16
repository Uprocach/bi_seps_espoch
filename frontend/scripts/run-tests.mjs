import { build } from "esbuild";
import { spawnSync } from "node:child_process";
import { mkdtempSync, readdirSync, rmSync, statSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, relative, resolve } from "node:path";

const frontendRoot = resolve(import.meta.dirname, "..");
const srcRoot = join(frontendRoot, "src");

function collectTestFiles(dir) {
  const results = [];
  for (const entry of readdirSync(dir)) {
    const full = join(dir, entry);
    const stat = statSync(full);
    if (stat.isDirectory()) {
      results.push(...collectTestFiles(full));
    } else if (entry.endsWith(".test.ts") || entry.endsWith(".test.tsx")) {
      results.push(full);
    }
  }
  return results;
}

const testFiles = collectTestFiles(srcRoot);
if (testFiles.length === 0) {
  console.log("No frontend *.test.ts(x) files found.");
  process.exit(0);
}

const outDir = mkdtempSync(join(tmpdir(), "sfps-fe-tests-"));
try {
  const outFiles = [];
  for (const entryFile of testFiles) {
    const rel = relative(srcRoot, entryFile).replace(/\.tsx?$/, ".mjs");
    const outfile = join(outDir, rel);
    await build({
      entryPoints: [entryFile],
      outfile,
      bundle: true,
      platform: "node",
      format: "esm",
      target: "node18",
      alias: { "@": srcRoot },
      logLevel: "silent",
    });
    outFiles.push(outfile);
  }

  const res = spawnSync(process.execPath, ["--test", ...outFiles], {
    stdio: "inherit",
  });
  process.exit(res.status ?? 1);
} finally {
  rmSync(outDir, { recursive: true, force: true });
}
