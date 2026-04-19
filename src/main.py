"""Main entry point for the Editing Tools GUI application.

A tkinter-based interface for loading documents and running
various proofreading/analysis tools.
"""

import csv
import io
import threading
import time
import tkinter as tk
from tkinter import filedialog, font, messagebox, ttk

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------


class App(tk.Tk):
    """Main application window."""

    def __init__(self):
        super().__init__()

        self.title("Editing Tools")
        self.minsize(720, 600)

        # State
        self._filepath: str = ""
        self._results_text: str = ""
        self._findings: list = []  # list[Finding] from all tools
        self._freq_result: dict | None = None  # word_frequency result

        self._build_ui()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self):
        """Build all widgets."""
        pad = {"padx": 12, "pady": 6}

        # ── File row ────────────────────────────────────────────────────
        file_frame = ttk.LabelFrame(self, text="Fil")
        file_frame.pack(fill="x", **pad)

        self._file_var = tk.StringVar()
        ttk.Entry(
            file_frame, textvariable=self._file_var, state="readonly", width=60
        ).pack(side="left", fill="x", expand=True, padx=(6, 4), pady=4)
        ttk.Button(file_frame, text="Välj fil", command=self._pick_file).pack(
            side="left", padx=(0, 6), pady=4
        )

        # ── Tools row ───────────────────────────────────────────────────
        tools_frame = ttk.LabelFrame(self, text="Verktyg")
        tools_frame.pack(fill="x", **pad)

        self._use_typo = tk.BooleanVar(value=True)
        self._use_newline = tk.BooleanVar(value=True)
        self._use_spell = tk.BooleanVar(value=True)
        self._use_freq = tk.BooleanVar(value=True)

        row1 = ttk.Frame(tools_frame)
        row1.pack(fill="x", padx=6, pady=(4, 0))
        ttk.Checkbutton(row1, text="Typografiska fel", variable=self._use_typo).pack(
            side="left", padx=(0, 20)
        )
        ttk.Checkbutton(row1, text="Radbrytningar", variable=self._use_newline).pack(
            side="left"
        )

        row2 = ttk.Frame(tools_frame)
        row2.pack(fill="x", padx=6, pady=(2, 4))
        ttk.Checkbutton(row2, text="Stavningskontroll", variable=self._use_spell).pack(
            side="left", padx=(0, 20)
        )
        ttk.Checkbutton(row2, text="Ordfrekvens", variable=self._use_freq).pack(
            side="left"
        )

        # Language radio buttons
        lang_frame = ttk.Frame(tools_frame)
        lang_frame.pack(fill="x", padx=6, pady=(0, 6))
        ttk.Label(lang_frame, text="Språk (stavning):").pack(side="left")
        self._lang_var = tk.StringVar(value="sv")
        ttk.Radiobutton(
            lang_frame, text="Svenska", variable=self._lang_var, value="sv"
        ).pack(side="left", padx=(8, 4))
        ttk.Radiobutton(
            lang_frame, text="Engelska", variable=self._lang_var, value="en"
        ).pack(side="left")

        # ── Run button ──────────────────────────────────────────────────
        run_frame = ttk.Frame(self)
        run_frame.pack(fill="x", **pad)

        self._run_btn = ttk.Button(
            run_frame, text="Kör analys", command=self._run_analysis
        )
        self._run_btn.pack(side="left")
        self._status_label = ttk.Label(run_frame, text="")
        self._status_label.pack(side="left", padx=10)

        # ── Results area ────────────────────────────────────────────────
        results_frame = ttk.LabelFrame(self, text="Resultat")
        results_frame.pack(fill="both", expand=True, **pad)

        # Header row with clear button
        hdr = ttk.Frame(results_frame)
        hdr.pack(fill="x", padx=4, pady=(2, 0))
        ttk.Button(hdr, text="Rensa", command=self._clear_results).pack(side="right")

        mono = font.Font(family="Menlo", size=11)
        text_frame = ttk.Frame(results_frame)
        text_frame.pack(fill="both", expand=True, padx=4, pady=4)

        self._results = tk.Text(
            text_frame,
            wrap="none",
            state="disabled",
            font=mono,
            relief="flat",
            bg="#f8f8f8",
        )
        vsb = ttk.Scrollbar(text_frame, orient="vertical", command=self._results.yview)
        hsb = ttk.Scrollbar(
            text_frame, orient="horizontal", command=self._results.xview
        )
        self._results.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        vsb.pack(side="right", fill="y")
        hsb.pack(side="bottom", fill="x")
        self._results.pack(fill="both", expand=True)

        # ── Export buttons ──────────────────────────────────────────────
        export_frame = ttk.Frame(self)
        export_frame.pack(fill="x", **pad)
        ttk.Button(export_frame, text="Spara som TXT", command=self._export_txt).pack(
            side="left", padx=(0, 6)
        )
        ttk.Button(export_frame, text="Spara som CSV", command=self._export_csv).pack(
            side="left", padx=(0, 6)
        )
        ttk.Button(export_frame, text="Spara båda", command=self._export_both).pack(
            side="left"
        )

    # ------------------------------------------------------------------
    # File picking
    # ------------------------------------------------------------------

    def _pick_file(self):
        path = filedialog.askopenfilename(
            title="Välj fil",
            filetypes=[
                ("Stödda filer", "*.pdf *.docx *.txt"),
                ("PDF", "*.pdf"),
                ("Word", "*.docx"),
                ("Text", "*.txt"),
                ("Alla filer", "*.*"),
            ],
        )
        if path:
            self._filepath = path
            self._file_var.set(path)

    # ------------------------------------------------------------------
    # Analysis
    # ------------------------------------------------------------------

    def _run_analysis(self):
        """Validate input and launch analysis in a background thread."""
        if not self._filepath:
            messagebox.showerror("Ingen fil vald", "Välj en fil innan du kör analysen.")
            return

        # Disable UI while running
        self._run_btn.configure(state="disabled")
        self._status_label.configure(text="Analyserar...")

        thread = threading.Thread(target=self._analyse_worker, daemon=True)
        thread.start()

    def _analyse_worker(self):
        """Run all selected tools in a background thread."""
        start = time.perf_counter()
        findings: list = []
        freq_result: dict | None = None
        output_parts: list[str] = []
        tool_count = 0

        try:
            # Parse document
            from src.parsers.parser_factory import get_parser

            extract_text = get_parser(self._filepath)
            text = extract_text(self._filepath)
        except Exception as exc:
            self._post_results(f"Fel vid inläsning av fil:\n{exc}\n", [], None, 0, 0.0)
            return

        # ── Typo checker ────────────────────────────────────────────────
        if self._use_typo.get():
            try:
                from src.tools.typo_checker import check as typo_check

                result = typo_check(text)
                findings.extend(result)
                output_parts.append(self._format_findings("Typografiska fel", result))
                tool_count += 1
            except Exception as exc:
                output_parts.append(f"=== Typografiska fel ===\nFel: {exc}\n")
                tool_count += 1

        # ── Newline checker ─────────────────────────────────────────────
        if self._use_newline.get():
            try:
                from src.tools.newline_checker import check as newline_check

                result = newline_check(text)
                findings.extend(result)
                output_parts.append(self._format_findings("Radbrytningar", result))
                tool_count += 1
            except Exception as exc:
                output_parts.append(f"=== Radbrytningar ===\nFel: {exc}\n")
                tool_count += 1

        # ── Spell checker ───────────────────────────────────────────────
        if self._use_spell.get():
            try:
                from src.tools.spell_checker import check as spell_check

                result = spell_check(text, lang=self._lang_var.get())
                findings.extend(result)
                output_parts.append(self._format_findings("Stavningskontroll", result))
                tool_count += 1
            except Exception as exc:
                output_parts.append(f"=== Stavningskontroll ===\nFel: {exc}\n")
                tool_count += 1

        # ── Word frequency ──────────────────────────────────────────────
        if self._use_freq.get():
            try:
                from src.tools.word_frequency import analyze as freq_analyze

                freq_result = freq_analyze(text, top_n=50)
                output_parts.append(self._format_frequency(freq_result))
                tool_count += 1
            except Exception as exc:
                output_parts.append(f"=== Ordfrekvens ===\nFel: {exc}\n")
                tool_count += 1

        elapsed = time.perf_counter() - start
        total_findings = len(findings)
        summary = (
            f"Analys klar. {total_findings} fynd från {tool_count} verktyg. "
            f"({elapsed:.1f}s)\n\n"
        )
        full_text = summary + "\n".join(output_parts)

        self._post_results(full_text, findings, freq_result, tool_count, elapsed)

    def _post_results(
        self, text: str, findings: list, freq_result, tool_count: int, elapsed: float
    ):
        """Push results back to the main thread."""
        self._results_text = text
        self._findings = findings
        self._freq_result = freq_result
        # Schedule UI update on the main thread
        self.after(0, lambda: self._update_results_ui(text))

    def _update_results_ui(self, text: str):
        """Update the results text area and re-enable the run button."""
        self._results.configure(state="normal")
        self._results.delete("1.0", "end")
        self._results.insert("end", text)
        self._results.configure(state="disabled")
        self._run_btn.configure(state="normal")
        self._status_label.configure(text="")

    # ------------------------------------------------------------------
    # Formatting helpers
    # ------------------------------------------------------------------

    def _format_findings(self, title: str, findings: list) -> str:
        """Format a list of Finding objects under a section header."""
        lines: list[str] = []
        lines.append(f"=== {title} ({len(findings)} fynd) ===")
        if not findings:
            lines.append("Inga fynd.")
        else:
            for f in findings:
                lines.append(
                    f"Rad {f.line_number:>4}, Kol {f.column:>3} | {f.description}"
                )
                if f.excerpt:
                    lines.append(f'                 | "{f.excerpt}"')
        lines.append("")
        return "\n".join(lines)

    def _format_frequency(self, result: dict) -> str:
        """Format word frequency results as a ranked table."""
        lines: list[str] = []
        lines.append("=== Ordfrekvens ===")

        total = result.get("total_words", 0)
        unique = result.get("unique_words", 0)
        avg_len = result.get("avg_word_length", 0.0)
        lines.append(
            f"Totalt antal ord: {total} | Unika ord: {unique} | Snittlängd: {avg_len:.1f}"
        )
        lines.append("")

        top: list[tuple[str, int]] = result.get("top_words", [])
        if top:
            col_width = max((len(w) for w, _ in top), default=10) + 2
            header = f" {'#':>3}   {'Ord':<{col_width}} {'Antal'}"
            lines.append(header)
            lines.append("─" * len(header))
            for rank, (word, count) in enumerate(top, start=1):
                lines.append(f" {rank:>3}   {word:<{col_width}} {count}")

        lines.append("")
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Results area controls
    # ------------------------------------------------------------------

    def _clear_results(self):
        self._results_text = ""
        self._findings = []
        self._freq_result = None
        self._results.configure(state="normal")
        self._results.delete("1.0", "end")
        self._results.configure(state="disabled")

    # ------------------------------------------------------------------
    # Export
    # ------------------------------------------------------------------

    def _stem(self) -> str:
        """Derive a base name from the loaded file path."""
        import os

        if self._filepath:
            base = os.path.basename(self._filepath)
            name, _ = os.path.splitext(base)
            return name
        return "rapport"

    def _export_txt(self) -> bool:
        """Save results as plain text. Returns True on success."""
        if not self._results_text:
            messagebox.showinfo("Inget att spara", "Kör en analys först.")
            return False

        default = f"{self._stem()}_rapport.txt"
        path = filedialog.asksaveasfilename(
            title="Spara som TXT",
            defaultextension=".txt",
            initialfile=default,
            filetypes=[("Textfil", "*.txt"), ("Alla filer", "*.*")],
        )
        if not path:
            return False

        try:
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(self._results_text)
        except Exception as exc:
            messagebox.showerror("Fel vid sparning", str(exc))
            return False
        return True

    def _export_csv(self) -> bool:
        """Save results as CSV. Returns True on success."""
        if not self._findings and self._freq_result is None:
            messagebox.showinfo("Inget att spara", "Kör en analys först.")
            return False

        default = f"{self._stem()}_rapport.csv"
        path = filedialog.asksaveasfilename(
            title="Spara som CSV",
            defaultextension=".csv",
            initialfile=default,
            filetypes=[("CSV-fil", "*.csv"), ("Alla filer", "*.*")],
        )
        if not path:
            return False

        try:
            with open(path, "w", newline="", encoding="utf-8") as fh:
                writer = csv.writer(fh)

                # Findings section
                writer.writerow(["verktyg", "rad", "kolumn", "beskrivning", "utdrag"])
                for f in self._findings:
                    writer.writerow(
                        [f.tool, f.line_number, f.column, f.description, f.excerpt]
                    )

                # Word frequency section (if available)
                if self._freq_result:
                    writer.writerow([])
                    writer.writerow(["=== Ordfrekvens ==="])
                    writer.writerow(["total_ord", "unika_ord", "snittlängd"])
                    writer.writerow(
                        [
                            self._freq_result.get("total_words", ""),
                            self._freq_result.get("unique_words", ""),
                            f"{self._freq_result.get('average_length', 0.0):.1f}",
                        ]
                    )
                    writer.writerow([])
                    writer.writerow(["rank", "ord", "antal"])
                    for rank, (word, count) in enumerate(
                        self._freq_result.get("top_words", []), start=1
                    ):
                        writer.writerow([rank, word, count])
        except Exception as exc:
            messagebox.showerror("Fel vid sparning", str(exc))
            return False
        return True

    def _export_both(self):
        """Save both TXT and CSV."""
        txt_ok = self._export_txt()
        if txt_ok:
            self._export_csv()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    app = App()
    app.mainloop()
