import { spawn, spawnSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const webDir = path.join(root, "apps", "web");
const backendDir = path.join(root, "apps", "backend");
const isWindows = process.platform === "win32";
const npm = isWindows ? "npm.cmd" : "npm";
const python = process.env.PYTHON || (isWindows ? "python" : "python3");

function run(command, args, options = {}) {
  const child = spawn(command, args, {
    cwd: root,
    stdio: ["ignore", "pipe", "pipe"],
    ...options,
  });

  child.stdout?.on("data", (data) => process.stdout.write(data));
  child.stderr?.on("data", (data) => process.stderr.write(data));

  return child;
}

function installWebDepsIfNeeded() {
  if (fs.existsSync(path.join(webDir, "node_modules"))) return;

  console.log("Installing frontend dependencies...");
  const result = spawnSync(npm, ["--prefix", "apps/web", "install"], {
    cwd: root,
    stdio: "inherit",
  });

  if (result.status !== 0) {
    process.exit(result.status ?? 1);
  }
}

installWebDepsIfNeeded();

console.log("Starting Bridge backend on http://127.0.0.1:8000");
const backend = run(
  python,
  ["-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000"],
  { cwd: backendDir },
);

console.log("Starting Bridge frontend on http://127.0.0.1:5173");
const viteBin = path.join(webDir, "node_modules", "vite", "bin", "vite.js");
const frontend = run(
  process.execPath,
  [viteBin, "--host", "127.0.0.1"],
  { cwd: webDir },
);

const children = [backend, frontend];
let shuttingDown = false;

function stopAll(code = 0) {
  if (shuttingDown) return;
  shuttingDown = true;

  for (const child of children) {
    if (child.killed || !child.pid) continue;
    if (isWindows) {
      spawnSync("taskkill", ["/pid", String(child.pid), "/t", "/f"], { stdio: "ignore" });
    } else {
      child.kill("SIGTERM");
    }
  }

  process.exit(code);
}

for (const child of children) {
  child.on("exit", (code) => {
    if (!shuttingDown && code && code !== 0) {
      stopAll(code);
    }
  });
}

process.on("SIGINT", () => stopAll(0));
process.on("SIGTERM", () => stopAll(0));

console.log("");
console.log("Bridge is starting.");
console.log("Frontend: http://127.0.0.1:5173");
console.log("Backend:  http://127.0.0.1:8000/health");
console.log("Press Ctrl+C to stop both.");
