/** Controls CLI streams and ANSI color behavior. */
export interface OutputOptions {
  color?: boolean;
  stdout?: NodeJS.WritableStream;
  stderr?: NodeJS.WritableStream;
}

const ansi = {
  reset: "\u001b[0m",
  bold: "\u001b[1m",
  green: "\u001b[32m",
  yellow: "\u001b[33m",
  red: "\u001b[31m",
  cyan: "\u001b[36m",
  magenta: "\u001b[35m",
  gray: "\u001b[90m",
};

/** Formats consistent human-readable CLI output for real or captured streams. */
export class CliOutput {
  readonly stdout: NodeJS.WritableStream;
  readonly stderr: NodeJS.WritableStream;
  readonly color: boolean;

  constructor(options: OutputOptions = {}) {
    this.stdout = options.stdout ?? process.stdout;
    this.stderr = options.stderr ?? process.stderr;
    this.color = options.color ?? (Boolean((this.stdout as NodeJS.WriteStream).isTTY) && process.env.NO_COLOR === undefined);
  }

  /** Applies an ANSI color only when color output is enabled. */
  paint(value: string, color: keyof typeof ansi): string {
    return this.color ? `${ansi[color]}${value}${ansi.reset}` : value;
  }

  /** Writes a normal line to standard output. */
  line(value = ""): void { this.stdout.write(`${value}\n`); }
  /** Writes an unformatted error line to standard error. */
  error(value: string): void { this.stderr.write(`${value}\n`); }
  /** Writes a highlighted section title. */
  title(value: string): void { this.line(this.paint(value, "magenta")); }
  /** Writes a successful labeled result. */
  pass(label: string, detail: string): void { this.line(`  ${this.paint("✓", "green")} ${label.padEnd(13)} ${detail}`); }
  /** Writes a warning labeled result. */
  warn(label: string, detail: string): void { this.line(`  ${this.paint("!", "yellow")} ${label.padEnd(13)} ${detail}`); }
  /** Writes a failed labeled result. */
  fail(label: string, detail: string): void { this.line(`  ${this.paint("✗", "red")} ${label.padEnd(13)} ${detail}`); }
}
