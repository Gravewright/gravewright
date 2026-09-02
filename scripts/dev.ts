import { spawn, type ChildProcess } from "node:child_process";

const npm = process.platform === "win32" ? "npm.cmd" : "npm";
const children: ChildProcess[] = [];
let stopping = false;

/** Starts a child process that shares the development terminal and environment. */
function start(args: string[]): ChildProcess {
  const child = spawn(npm, args, { stdio: "inherit", env: process.env });
  children.push(child);
  child.once("exit", (code, signal) => {
    if (stopping) return;
    stopping = true;
    for (const sibling of children) if (sibling !== child && sibling.exitCode === null) sibling.kill("SIGTERM");
    process.exitCode = code ?? (signal ? 1 : 0);
  });
  return child;
}

/** Forwards a termination signal to every running development child. */
function stop(signal: NodeJS.Signals): void {
  if (stopping) return;
  stopping = true;
  for (const child of children) if (child.exitCode === null) child.kill(signal);
}

process.once("SIGINT", () => stop("SIGINT"));
process.once("SIGTERM", () => stop("SIGTERM"));

start(["--prefix", "modules/gravewright-room", "run", "dev"]);
start(["exec", "--", "tsx", "watch", "src/cli/main.ts", "run"]);
