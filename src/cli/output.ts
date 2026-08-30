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

export class CliOutput {
  readonly stdout: NodeJS.WritableStream;
  readonly stderr: NodeJS.WritableStream;
  readonly color: boolean;

  constructor(options: OutputOptions = {}) {
    this.stdout = options.stdout ?? process.stdout;
    this.stderr = options.stderr ?? process.stderr;
    this.color = options.color ?? (Boolean((this.stdout as NodeJS.WriteStream).isTTY) && process.env.NO_COLOR === undefined);
  }

  paint(value: string, color: keyof typeof ansi): string {
    return this.color ? `${ansi[color]}${value}${ansi.reset}` : value;
  }

  line(value = ""): void { this.stdout.write(`${value}\n`); }
  error(value: string): void { this.stderr.write(`${value}\n`); }
  title(value: string): void { this.line(this.paint(value, "magenta")); }
  pass(label: string, detail: string): void { this.line(`  ${this.paint("✓", "green")} ${label.padEnd(13)} ${detail}`); }
  warn(label: string, detail: string): void { this.line(`  ${this.paint("!", "yellow")} ${label.padEnd(13)} ${detail}`); }
  fail(label: string, detail: string): void { this.line(`  ${this.paint("✗", "red")} ${label.padEnd(13)} ${detail}`); }
}
