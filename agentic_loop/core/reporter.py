"""Prints each loop stage and saves the run as Markdown evidence for the Release 1 report."""

from datetime import datetime
from pathlib import Path


REPORT_DIR = Path(__file__).resolve().parents[2] / "docs" / "release-1" / "agentic-loop"


class Reporter:
    def __init__(self, mode):
        self.mode = mode
        self.started = datetime.now().astimezone()
        self.lines = [
            f"# Shared Agentic Loop — {mode.upper()} validation mode",
            "",
            f"Run: {self.started.isoformat(timespec='seconds')}",
            "",
        ]

    def stage(self, name, text=""):
        print(f"\n{name}:" + (f" {text}" if text else ""))
        self.lines += [f"## {name}", ""] + ([text, ""] if text else [])

    def line(self, text):
        print(f"  {text}")
        self.lines.append(f"- {text}")

    def table(self, headers, rows):
        widths = [max(len(str(h)), *(len(str(r[i])) for r in rows)) for i, h in enumerate(headers)] if rows else [len(h) for h in headers]
        print("  " + " | ".join(str(h).ljust(w) for h, w in zip(headers, widths)))
        print("  " + "-+-".join("-" * w for w in widths))
        for row in rows:
            print("  " + " | ".join(str(c).ljust(w) for c, w in zip(row, widths)))
        self.lines += [
            "| " + " | ".join(headers) + " |",
            "|" + "---|" * len(headers),
            *("| " + " | ".join(str(c).replace("|", "\\|") for c in row) + " |" for row in rows),
            "",
        ]

    def block(self, text):
        print("  " + text.replace("\n", "\n  "))
        self.lines += ["```", text, "```", ""]

    def save(self):
        REPORT_DIR.mkdir(parents=True, exist_ok=True)
        path = REPORT_DIR / f"{self.mode}-validation.md"
        path.write_text("\n".join(self.lines) + "\n", encoding="utf-8")
        print(f"\nSaved: {path.relative_to(REPORT_DIR.parents[2])}")
        return path
