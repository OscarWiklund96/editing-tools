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
# Constants
# ---------------------------------------------------------------------------

TOOL_NAMES = {
    "spell": "Stavningskontroll",
    "typo": "Typografiska fel",
    "consistency": "Konsistenskontroll",
    "dialogue": "Dialogkontroll",
    "newline": "Radbrytningar",
    "sentence": "Meningslängd",
    "chapter_balance": "Kapitelbalans",
    "heading": "Rubrikhierarki",
    "freq": "Ordfrekvens",
    "repetition": "Upprepningsdetektor",
    "page_ref": "Sidreferenser",
}

TOOL_CATEGORIES = [
    ("Språk & grammatik", ["spell", "typo", "consistency", "dialogue"]),
    ("Struktur & formatering", ["newline", "sentence", "chapter_balance", "heading"]),
    ("Analys", ["freq", "repetition", "page_ref"]),
]

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
        self._sentence_stats: dict | None = None  # sentence_length stats
        self._chapter_result: dict | None = None  # chapter_balance result

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

        # ── Tool selection ──────────────────────────────────────────────
        tools_frame = ttk.LabelFrame(self, text="Välj verktyg")
        tools_frame.pack(fill="x", **pad)

        self._tool_var = tk.StringVar(value="spell")

        bold_font = font.Font(weight="bold", size=10)

        for cat_name, tool_keys in TOOL_CATEGORIES:
            ttk.Label(tools_frame, text=cat_name, font=bold_font).pack(
                anchor="w", padx=6, pady=(6, 0)
            )
            for key in tool_keys:
                ttk.Radiobutton(
                    tools_frame,
                    text=TOOL_NAMES[key],
                    variable=self._tool_var,
                    value=key,
                ).pack(anchor="w", padx=24, pady=1)

        # ── Tool-specific options ───────────────────────────────────────
        sep = ttk.Separator(tools_frame, orient="horizontal")
        sep.pack(fill="x", padx=6, pady=(8, 2))
        ttk.Label(tools_frame, text="Inställningar", font=bold_font).pack(
            anchor="w", padx=6, pady=(2, 4)
        )

        self._options_frame = ttk.Frame(tools_frame)
        self._options_frame.pack(fill="x", padx=24, pady=(0, 6))

        # -- Spell language options --
        self._spell_options = ttk.Frame(self._options_frame)
        self._lang_var = tk.StringVar(value="sv")
        ttk.Label(self._spell_options, text="Språk:").pack(side="left")
        for label, val in [
            ("Svenska", "sv"),
            ("English", "en"),
            ("Tyska", "de"),
            ("Franska", "fr"),
            ("Spanska", "es"),
        ]:
            ttk.Radiobutton(
                self._spell_options, text=label, variable=self._lang_var, value=val
            ).pack(side="left", padx=(8, 0))

        # -- Frequency options --
        self._freq_options = ttk.Frame(self._options_frame)
        self._freq_sort_var = tk.StringVar(value="freq")
        self._freq_filter_var = tk.StringVar(value="min")
        self._freq_filter_n = tk.StringVar(value="2")

        ttk.Label(self._freq_options, text="Sortering:").pack(side="left")
        ttk.Radiobutton(
            self._freq_options,
            text="Frekvens",
            variable=self._freq_sort_var,
            value="freq",
        ).pack(side="left", padx=(4, 0))
        ttk.Radiobutton(
            self._freq_options, text="A–Ö", variable=self._freq_sort_var, value="alpha"
        ).pack(side="left", padx=(4, 16))

        ttk.Label(self._freq_options, text="Filter:").pack(side="left")
        ttk.Radiobutton(
            self._freq_options,
            text="Ingen",
            variable=self._freq_filter_var,
            value="none",
        ).pack(side="left", padx=(4, 0))
        ttk.Radiobutton(
            self._freq_options,
            text="Minst",
            variable=self._freq_filter_var,
            value="min",
        ).pack(side="left", padx=(4, 0))
        ttk.Radiobutton(
            self._freq_options,
            text="Högst",
            variable=self._freq_filter_var,
            value="max",
        ).pack(side="left", padx=(4, 8))
        ttk.Entry(self._freq_options, textvariable=self._freq_filter_n, width=4).pack(
            side="left", padx=(0, 4)
        )
        ttk.Label(self._freq_options, text="förekomster").pack(side="left")

        # -- Sentence length options --
        self._sentence_options = ttk.Frame(self._options_frame)
        self._sentence_max_var = tk.StringVar(value="40")
        self._sentence_min_var = tk.StringVar(value="3")

        ttk.Label(self._sentence_options, text="Max ord per mening:").pack(side="left")
        ttk.Entry(
            self._sentence_options, textvariable=self._sentence_max_var, width=5
        ).pack(side="left", padx=(4, 16))
        ttk.Label(self._sentence_options, text="Min ord per mening:").pack(side="left")
        ttk.Entry(
            self._sentence_options, textvariable=self._sentence_min_var, width=5
        ).pack(side="left", padx=(4, 0))

        # -- No-options placeholder --
        self._no_options = ttk.Label(self._options_frame, text="Inga inställningar")

        # Wire up dynamic options display
        self._tool_var.trace_add("write", self._on_tool_changed)
        self._on_tool_changed()  # show initial state

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
    # Dynamic options panel
    # ------------------------------------------------------------------

    def _on_tool_changed(self, *_args):
        """Show/hide tool-specific options based on the selected tool."""
        # Hide all option panels
        self._spell_options.pack_forget()
        self._freq_options.pack_forget()
        self._sentence_options.pack_forget()
        self._no_options.pack_forget()

        tool = self._tool_var.get()
        if tool == "spell":
            self._spell_options.pack(fill="x")
        elif tool == "freq":
            self._freq_options.pack(fill="x")
        elif tool == "sentence":
            self._sentence_options.pack(fill="x")
        else:
            self._no_options.pack(anchor="w")

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
        """Run the selected tool in a background thread."""
        start = time.perf_counter()
        findings: list = []
        freq_result: dict | None = None
        sentence_stats: dict | None = None
        chapter_result: dict | None = None
        output: str = ""
        tool = self._tool_var.get()
        tool_name = TOOL_NAMES.get(tool, tool)

        try:
            # Parse document
            from src.parsers.parser_factory import get_parser

            extract_text = get_parser(self._filepath)
            text = extract_text(self._filepath)
        except Exception as exc:
            self._post_results(
                f"Fel vid inläsning av fil:\n{exc}\n", [], None, None, None, 0, 0.0
            )
            return

        try:
            if tool == "spell":
                from src.tools.spell_checker import check as spell_check

                result = spell_check(text, lang=self._lang_var.get())
                findings.extend(result)
                output = self._format_findings("Stavningskontroll", result)

            elif tool == "typo":
                from src.tools.typo_checker import check as typo_check

                result = typo_check(text)
                findings.extend(result)
                output = self._format_findings("Typografiska fel", result)

            elif tool == "consistency":
                from src.tools.consistency_checker import check as consistency_check

                result = consistency_check(text)
                findings.extend(result)
                output = self._format_findings("Konsistenskontroll", result)

            elif tool == "newline":
                from src.tools.newline_checker import check as newline_check

                result = newline_check(text)
                findings.extend(result)
                output = self._format_findings("Radbrytningar", result)

            elif tool == "sentence":
                from src.tools.sentence_length import check as sentence_check

                try:
                    max_w = int(self._sentence_max_var.get())
                    min_w = int(self._sentence_min_var.get())
                except ValueError:
                    output = "=== Meningslängd ===\nFel: Ange giltiga heltal för max/min ord.\n"
                    self._post_results(
                        output, [], None, None, None, 1, time.perf_counter() - start
                    )
                    return
                result = sentence_check(text, max_words=max_w, min_words=min_w)
                sentence_findings = result["findings"]
                sentence_stats = result["stats"]
                findings.extend(sentence_findings)
                output = self._format_sentence_stats(sentence_findings, sentence_stats)

            elif tool == "freq":
                from src.tools.word_frequency import analyze as freq_analyze

                freq_result = freq_analyze(text)
                output = self._format_frequency(freq_result)

            elif tool == "repetition":
                from src.tools.repetition_detector import check as repetition_check

                result = repetition_check(text)
                findings.extend(result)
                output = self._format_findings("Upprepningsdetektor", result)

            elif tool == "dialogue":
                from src.tools.dialogue_checker import check as dialogue_check

                result = dialogue_check(text)
                findings.extend(result)
                output = self._format_findings("Dialogkontroll", result)

            elif tool == "chapter_balance":
                from src.tools.chapter_balance import check as chapter_check

                ch_result = chapter_check(text)
                chapter_result = ch_result
                chapter_findings = ch_result["findings"]
                findings.extend(chapter_findings)
                output = self._format_chapter_balance(ch_result)

            elif tool == "heading":
                from src.tools.heading_hierarchy import check as heading_check

                result = heading_check(text)
                findings.extend(result)
                output = self._format_findings("Rubrikhierarki", result)

            elif tool == "page_ref":
                from src.tools.page_reference_checker import check as pageref_check

                result = pageref_check(text)
                findings.extend(result)
                output = self._format_findings("Sidreferenser", result)

        except Exception as exc:
            output = f"=== {tool_name} ===\nFel: {exc}\n"

        elapsed = time.perf_counter() - start
        total_findings = len(findings)
        if freq_result is not None:
            count_label = f"{freq_result.get('unique_words', 0)} unika ord"
        else:
            count_label = f"{total_findings} fynd"
        summary = f"Analys klar: {tool_name} — {count_label}. ({elapsed:.1f}s)\n\n"
        full_text = summary + output

        self._post_results(
            full_text, findings, freq_result, sentence_stats, chapter_result, 1, elapsed
        )

    def _post_results(
        self,
        text: str,
        findings: list,
        freq_result,
        sentence_stats,
        chapter_result,
        tool_count: int,
        elapsed: float,
    ):
        """Push results back to the main thread."""
        self._results_text = text
        self._findings = findings
        self._freq_result = freq_result
        self._sentence_stats = sentence_stats
        self._chapter_result = chapter_result
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

    def _apply_freq_filters(self, words: list) -> list:
        """Apply the current sort/filter UI settings to a word-frequency list."""
        filter_mode = self._freq_filter_var.get()
        try:
            n = int(self._freq_filter_n.get())
        except ValueError:
            n = 0

        if filter_mode == "min" and n > 0:
            words = [(w, c) for w, c in words if c >= n]
        elif filter_mode == "max" and n > 0:
            words = [(w, c) for w, c in words if c <= n]

        if self._freq_sort_var.get() == "alpha":
            words = sorted(words, key=lambda x: x[0])
        # else: already sorted by frequency from analyze()

        return words

    def _format_frequency(self, result: dict) -> str:
        """Format word frequency results as a ranked table."""
        lines: list[str] = []

        total = result.get("total_words", 0)
        unique = result.get("unique_words", 0)
        avg_len = result.get("avg_word_length", 0.0)

        words = self._apply_freq_filters(result.get("top_words", []))

        lines.append(f"=== Ordfrekvens ({len(words)} ord) ===")
        lines.append(
            f"Totalt antal ord: {total} | Unika ord: {unique} | Snittlängd: {avg_len:.1f}"
        )
        lines.append("")

        if words:
            col_width = max((len(w) for w, _ in words), default=10) + 2
            header = f" {'#':>3}   {'Ord':<{col_width}} {'Antal'}"
            lines.append(header)
            lines.append("─" * len(header))
            for rank, (word, count) in enumerate(words, start=1):
                lines.append(f" {rank:>3}   {word:<{col_width}} {count}")

        lines.append("")
        return "\n".join(lines)

    def _format_sentence_stats(self, findings: list, stats: dict) -> str:
        """Format sentence length findings with histogram and stats."""
        lines: list[str] = []

        total = stats.get("total_sentences", 0)
        avg = stats.get("avg_words", 0.0)
        shortest = stats.get("min_words", 0)
        longest = stats.get("max_words", 0)
        distribution = stats.get("distribution", [])

        lines.append(f"=== Meningslängd ({len(findings)} fynd) ===")
        lines.append(
            f"Totalt antal meningar: {total} | Snittlängd: {avg:.1f} ord "
            f"| Kortast: {shortest} | Längst: {longest}"
        )
        lines.append("")

        # Histogram
        max_count = max((c for _, c in distribution), default=1) or 1
        max_bar = 20

        lines.append("Fördelning:")
        for label, count in distribution:
            bar_len = round(count / max_count * max_bar) if count > 0 else 0
            bar = "█" * bar_len if bar_len > 0 else "░"
            lines.append(f"  {label + ' ord':<12} {bar} {count}")
        lines.append("")

        # Flagged sentences
        if findings:
            lines.append("Flaggade meningar:")
            for f in findings:
                lines.append(
                    f"Rad {f.line_number:>4}, Kol {f.column:>3} | {f.description}"
                )
                if f.excerpt:
                    lines.append(f'                 | "{f.excerpt}"')
        else:
            lines.append("Inga flaggade meningar.")

        lines.append("")
        return "\n".join(lines)

    def _format_chapter_balance(self, result: dict) -> str:
        """Format chapter balance results as a table plus findings."""
        lines: list[str] = []
        chapters = result.get("chapters", [])
        findings = result.get("findings", [])

        lines.append(
            f"=== Kapitelbalans ({len(chapters)} kapitel, {len(findings)} fynd) ==="
        )
        lines.append("")

        if chapters:
            name_width = max(len(ch["name"][:40]) for ch in chapters) + 2
            header = f" {'Rad':>5}  {'Kapitel':<{name_width}} {'Ord':>6}"
            lines.append(header)
            lines.append("─" * len(header))
            for ch in chapters:
                name = ch["name"][:40]
                lines.append(
                    f" {ch['line_number']:>5}  {name:<{name_width}} {ch['word_count']:>6}"
                )
            lines.append("")

        if findings:
            lines.append("Flaggade kapitel:")
            for f in findings:
                lines.append(
                    f"Rad {f.line_number:>4}, Kol {f.column:>3} | {f.description}"
                )
        else:
            lines.append("Inga obalanserade kapitel hittades.")

        lines.append("")
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Results area controls
    # ------------------------------------------------------------------

    def _clear_results(self):
        self._results_text = ""
        self._findings = []
        self._freq_result = None
        self._sentence_stats = None
        self._chapter_result = None
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
        if (
            not self._findings
            and self._freq_result is None
            and self._sentence_stats is None
            and self._chapter_result is None
        ):
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
                if self._findings:
                    writer.writerow(
                        ["verktyg", "rad", "kolumn", "beskrivning", "utdrag"]
                    )
                    for f in self._findings:
                        writer.writerow(
                            [f.tool, f.line_number, f.column, f.description, f.excerpt]
                        )

                # Word frequency section (if available)
                if self._freq_result:
                    writer.writerow(["=== Ordfrekvens ==="])
                    writer.writerow(["total_ord", "unika_ord", "snittlängd"])
                    writer.writerow(
                        [
                            self._freq_result.get("total_words", ""),
                            self._freq_result.get("unique_words", ""),
                            f"{self._freq_result.get('avg_word_length', 0.0):.1f}",
                        ]
                    )
                    writer.writerow([])
                    writer.writerow(["rank", "ord", "antal"])
                    words = self._apply_freq_filters(
                        self._freq_result.get("top_words", [])
                    )
                    for rank, (word, count) in enumerate(words, start=1):
                        writer.writerow([rank, word, count])

                # Sentence stats section (if available)
                if self._sentence_stats:
                    writer.writerow(["=== Meningslängd ==="])
                    writer.writerow(
                        ["totalt_meningar", "snittlängd", "kortast", "längst"]
                    )
                    writer.writerow(
                        [
                            self._sentence_stats.get("total_sentences", ""),
                            f"{self._sentence_stats.get('avg_words', 0.0):.1f}",
                            self._sentence_stats.get("min_words", ""),
                            self._sentence_stats.get("max_words", ""),
                        ]
                    )
                    distribution = self._sentence_stats.get("distribution", [])
                    if distribution:
                        writer.writerow([])
                        writer.writerow(["intervall", "antal"])
                        for label, count in distribution:
                            writer.writerow([label, count])

                # Chapter balance section (if available)
                if self._chapter_result:
                    writer.writerow(["=== Kapitelbalans ==="])
                    writer.writerow(["rad", "kapitel", "ordantal"])
                    for ch in self._chapter_result.get("chapters", []):
                        writer.writerow(
                            [ch["line_number"], ch["name"], ch["word_count"]]
                        )

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
