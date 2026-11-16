import { readdirSync, readFileSync, statSync } from "node:fs";
import { join, relative, resolve } from "node:path";

const repoRoot = resolve(import.meta.dirname, "..");
const violations = [];

function walk(dir, exts) {
  const files = [];
  for (const entry of readdirSync(dir)) {
    if (entry === "node_modules" || entry === ".venv" || entry === "__pycache__" || entry === "dist") {
      continue;
    }
    const full = join(dir, entry);
    const stat = statSync(full);
    if (stat.isDirectory()) {
      files.push(...walk(full, exts));
    } else if (exts.some((ext) => entry.endsWith(ext))) {
      files.push(full);
    }
  }
  return files;
}

const frontendSrc = join(repoRoot, "frontend", "src");
const httpClientPath = join(frontendSrc, "services", "httpClient.ts");

for (const file of walk(frontendSrc, [".ts", ".tsx"])) {
  const rel = relative(repoRoot, file).replace(/\\/g, "/");
  const content = readFileSync(file, "utf8");

  if (file !== httpClientPath && /\bfetch\s*\(/.test(content)) {
    violations.push(`${rel}: raw fetch() is banned outside frontend/src/services/httpClient.ts`);
  }

  if (/@\/services\/(apiClient|proClient)\b/.test(content)) {
    violations.push(`${rel}: imports removed shim (apiClient/proClient); use @/services/httpClient`);
  }

  if (
    !rel.endsWith("src/types/api.ts") &&
    !rel.endsWith("src/services/httpClient.ts") &&
    /\bexport\s+(?:interface|type)\s+Benchmarking(?:CompareResponse|IndicatorRow)\b/.test(content)
  ) {
    violations.push(`${rel}: duplicate Benchmarking* type definition; import from @/services/httpClient or @/types/api`);
  }
}

for (const pyRoot of [join(repoRoot, "backend"), join(repoRoot, "etl")]) {
  for (const file of walk(pyRoot, [".py"])) {
    const rel = relative(repoRoot, file).replace(/\\/g, "/");
    const content = readFileSync(file, "utf8");
    if (/\b(?:benchmarking_service|export_service)\b/.test(content)) {
      violations.push(`${rel}: references removed backend module (benchmarking_service/export_service)`);
    }
  }
}

if (violations.length > 0) {
  console.error("Guardrail violations detected:");
  for (const v of violations) {
    console.error(` - ${v}`);
  }
  process.exit(1);
}

console.log("Guardrails check passed.");
