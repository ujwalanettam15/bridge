import { spawn } from "node:child_process";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const backendDir = path.join(root, "apps", "backend");
const python = process.env.PYTHON || (process.platform === "win32" ? "python" : "python3");

const child = spawn(
  python,
  ["-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000"],
  {
    cwd: backendDir,
    stdio: "inherit",
  },
);

child.on("exit", (code) => process.exit(code ?? 0));
