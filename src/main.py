"""Main entry point for the Editing Tools GUI application.

A customtkinter-based interface for loading documents and running
various proofreading/analysis tools.
"""

import csv
import io
import os
import threading
import time
import tkinter as tk
from tkinter import filedialog, messagebox

import customtkinter as ctk

# ---------------------------------------------------------------------------
# Appearance
# ---------------------------------------------------------------------------

ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

TOOL_NAMES = {
    "spell": "Stavningskontroll",
    "typo": "Typografiska fel",
    "newline": "Radbrytningar",
    "sentence": "Meningslängd",
    "freq": "Ordfrekvens",
    "repetition": "Upprepningsdetektor",
    "pdf2docx": "PDF → DOCX",
}

TOOL_CATEGORIES = [
    ("Språk & grammatik", ["spell", "typo"]),
    ("Struktur & formatering", ["newline", "sentence"]),
    ("Analys", ["freq", "repetition"]),
    ("Verktyg", ["pdf2docx"]),
]

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------


class App(ctk.CTk):
    """Main application window."""

    def __init__(self):
        super().__init__()

        self.title("Editing Tools")
        self.minsize(860, 580)

        # State
        self._filepath: str = ""
        self._results_text: str = ""
        self._findings: list = []
        self._freq_result: dict | None = None
        self._sentence_stats: dict | None = None
        self._fix_data: dict | None = None

        self._build_ui()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self):
        """Build all widgets."""
        # Fonts
        # Use system font (SF Pro on macOS) for a native iOS feel
        _sf = "SF Pro Text"  # falls back to system default if unavailable
        self._font_heading = ctk.CTkFont(family=_sf, size=20, weight="bold")
        self._font_category = ctk.CTkFont(family=_sf, size=12, weight="bold")
        self._font_normal = ctk.CTkFont(family=_sf, size=13)
        self._font_small = ctk.CTkFont(family=_sf, size=12)
        self._font_mono = ctk.CTkFont(family="SF Mono", size=11)

        # Grid layout: sidebar | main
        self.grid_columnconfigure(0, weight=0, minsize=280)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # ── Sidebar outer frame ──────────────────────────────────────────
        sidebar = ctk.CTkFrame(
            self,
            width=280,
            corner_radius=0,
            fg_color=("#f2f2f7", "#1c1c1e"),  # iOS system gray 6
        )
        sidebar.grid(row=0, column=0, sticky="nsew")
        sidebar.grid_propagate(False)
        sidebar.grid_rowconfigure(1, weight=1)  # scrollable area expands
        sidebar.grid_columnconfigure(0, weight=1)

        # ── Header (always visible) ──────────────────────────────────────
        header = ctk.CTkFrame(sidebar, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew")
        ctk.CTkLabel(header, text="📄 Editing Tools", font=self._font_heading).pack(
            padx=16, pady=(20, 12), anchor="w"
        )

        # ── Scrollable content ───────────────────────────────────────────
        scroll = ctk.CTkScrollableFrame(
            sidebar,
            fg_color="transparent",
            scrollbar_button_color=("#d1d1d6", "#48484a"),
        )
        scroll.grid(row=1, column=0, sticky="nsew")

        # ── Bottom bar (always visible) ──────────────────────────────────
        bottom = ctk.CTkFrame(sidebar, fg_color="transparent")
        bottom.grid(row=2, column=0, sticky="ew", padx=16, pady=(4, 16))

        # ── File picker ─────────────────────────────────────────────────
        ctk.CTkLabel(scroll, text="Fil", font=self._font_category).pack(
            padx=16, pady=(8, 4), anchor="w"
        )
        ctk.CTkButton(
            scroll, text="Välj fil...", command=self._pick_file, width=140
        ).pack(padx=16, pady=(0, 4), anchor="w")

        self._file_label = ctk.CTkLabel(
            scroll,
            text="Ingen fil vald",
            font=self._font_small,
            text_color="gray",
            wraplength=240,
        )
        self._file_label.pack(padx=16, pady=(0, 12), anchor="w")

        # ── Tool selection ──────────────────────────────────────────────
        self._tool_var = tk.StringVar(value="spell")

        for cat_name, tool_keys in TOOL_CATEGORIES:
            ctk.CTkLabel(
                scroll,
                text=cat_name.upper(),
                font=self._font_category,
                text_color=("#6e6e73", "#8e8e93"),  # iOS secondary label
            ).pack(padx=16, pady=(12, 4), anchor="w")
            for key in tool_keys:
                ctk.CTkRadioButton(
                    scroll,
                    text=TOOL_NAMES[key],
                    variable=self._tool_var,
                    value=key,
                    font=self._font_normal,
                ).pack(padx=32, pady=2, anchor="w")

        # ── Tool-specific options ───────────────────────────────────────
        sep = ctk.CTkFrame(
            scroll, height=1, fg_color=("#d1d1d6", "#38383a")
        )  # iOS separator
        sep.pack(fill="x", padx=16, pady=(16, 8))

        # ── Comment author name ────────────────────────────────────────
        ctk.CTkLabel(
            scroll,
            text="SPÅRADE ÄNDRINGAR",
            font=self._font_category,
            text_color=("#6e6e73", "#8e8e93"),
        ).pack(padx=16, pady=(12, 4), anchor="w")
        self._author_var = tk.StringVar(value="Editing Tools")
        ctk.CTkLabel(scroll, text="Författare:", font=self._font_small).pack(
            padx=16, pady=(0, 2), anchor="w"
        )
        ctk.CTkEntry(
            scroll,
            textvariable=self._author_var,
            font=self._font_small,
            width=200,
            placeholder_text="Namn i kommentarer",
        ).pack(padx=16, pady=(0, 8), anchor="w")

        sep2 = ctk.CTkFrame(scroll, height=1, fg_color=("#d1d1d6", "#38383a"))
        sep2.pack(fill="x", padx=16, pady=(8, 8))

        ctk.CTkLabel(scroll, text="Inställningar", font=self._font_category).pack(
            padx=16, pady=(0, 4), anchor="w"
        )

        self._options_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        self._options_frame.pack(fill="x", padx=16, pady=(0, 8))

        # -- Spell language options --
        self._spell_options = ctk.CTkFrame(self._options_frame, fg_color="transparent")
        self._lang_var = tk.StringVar(value="sv")
        ctk.CTkLabel(self._spell_options, text="Språk:", font=self._font_small).pack(
            anchor="w"
        )
        for label, val in [
            ("Svenska", "sv"),
            ("English", "en"),
            ("Tyska", "de"),
            ("Franska", "fr"),
            ("Spanska", "es"),
        ]:
            ctk.CTkRadioButton(
                self._spell_options,
                text=label,
                variable=self._lang_var,
                value=val,
                font=self._font_small,
            ).pack(anchor="w", padx=8, pady=1)

        # -- Frequency options --
        self._freq_options = ctk.CTkFrame(self._options_frame, fg_color="transparent")
        self._freq_sort_var = tk.StringVar(value="freq")
        self._freq_filter_var = tk.StringVar(value="min")
        self._freq_filter_n = tk.StringVar(value="2")

        ctk.CTkLabel(self._freq_options, text="Sortering:", font=self._font_small).pack(
            anchor="w"
        )
        row_sort = ctk.CTkFrame(self._freq_options, fg_color="transparent")
        row_sort.pack(anchor="w", padx=8)
        ctk.CTkRadioButton(
            row_sort,
            text="Frekvens",
            variable=self._freq_sort_var,
            value="freq",
            font=self._font_small,
        ).pack(side="left", padx=(0, 8))
        ctk.CTkRadioButton(
            row_sort,
            text="A–Ö",
            variable=self._freq_sort_var,
            value="alpha",
            font=self._font_small,
        ).pack(side="left")

        ctk.CTkLabel(self._freq_options, text="Filter:", font=self._font_small).pack(
            anchor="w", pady=(6, 0)
        )
        row_filter = ctk.CTkFrame(self._freq_options, fg_color="transparent")
        row_filter.pack(anchor="w", padx=8)
        ctk.CTkRadioButton(
            row_filter,
            text="Ingen",
            variable=self._freq_filter_var,
            value="none",
            font=self._font_small,
        ).pack(side="left", padx=(0, 4))
        ctk.CTkRadioButton(
            row_filter,
            text="Minst",
            variable=self._freq_filter_var,
            value="min",
            font=self._font_small,
        ).pack(side="left", padx=(0, 4))
        ctk.CTkRadioButton(
            row_filter,
            text="Högst",
            variable=self._freq_filter_var,
            value="max",
            font=self._font_small,
        ).pack(side="left")

        row_n = ctk.CTkFrame(self._freq_options, fg_color="transparent")
        row_n.pack(anchor="w", padx=8, pady=(4, 0))
        ctk.CTkEntry(
            row_n, textvariable=self._freq_filter_n, width=50, font=self._font_small
        ).pack(side="left", padx=(0, 4))
        ctk.CTkLabel(row_n, text="förekomster", font=self._font_small).pack(side="left")

        # -- Sentence length options --
        self._sentence_options = ctk.CTkFrame(
            self._options_frame, fg_color="transparent"
        )
        self._sentence_max_var = tk.StringVar(value="40")
        self._sentence_min_var = tk.StringVar(value="3")

        ctk.CTkLabel(
            self._sentence_options, text="Max ord per mening:", font=self._font_small
        ).pack(anchor="w")
        ctk.CTkEntry(
            self._sentence_options,
            textvariable=self._sentence_max_var,
            width=60,
            font=self._font_small,
        ).pack(anchor="w", padx=8, pady=(0, 4))
        ctk.CTkLabel(
            self._sentence_options, text="Min ord per mening:", font=self._font_small
        ).pack(anchor="w")
        ctk.CTkEntry(
            self._sentence_options,
            textvariable=self._sentence_min_var,
            width=60,
            font=self._font_small,
        ).pack(anchor="w", padx=8)

        # -- No-options placeholder --
        self._no_options = ctk.CTkLabel(
            self._options_frame,
            text="Inga inställningar",
            font=self._font_small,
            text_color="gray",
        )

        # Wire up dynamic options display
        self._tool_var.trace_add("write", self._on_tool_changed)
        self._on_tool_changed()

        # ── Run button + progress (in bottom bar) ───────────────────────
        self._run_btn = ctk.CTkButton(
            bottom,
            text="▶  Kör analys",
            command=self._run_analysis,
            height=42,
            corner_radius=10,
            font=ctk.CTkFont(family=_sf, size=15, weight="bold"),
        )
        self._run_btn.pack(fill="x", pady=(0, 6))

        self._progress = ctk.CTkProgressBar(bottom)
        self._progress.set(0)
        self._progress.pack(fill="x", pady=(0, 2))
        self._progress.pack_forget()

        self._status_label = ctk.CTkLabel(
            bottom, text="", font=self._font_small, text_color="gray"
        )
        self._status_label.pack(anchor="w")

        # ── Main area ──────────────────────────────────────────────────
        main = ctk.CTkFrame(self, corner_radius=0, fg_color=("#ffffff", "#000000"))
        main.grid(row=0, column=1, sticky="nsew", padx=(4, 0))
        main.grid_rowconfigure(1, weight=1)
        main.grid_columnconfigure(0, weight=1)

        # Toolbar
        toolbar = ctk.CTkFrame(main, fg_color="transparent")
        toolbar.grid(row=0, column=0, sticky="ew", padx=12, pady=(12, 4))

        self._fix_btn = ctk.CTkButton(
            toolbar,
            text="✏️ Autofixa",
            command=self._autofix,
            state="disabled",
            width=110,
        )
        self._fix_btn.pack(side="left", padx=(0, 8))
        self._track_btn = ctk.CTkButton(
            toolbar,
            text="📝 Spåra ändringar",
            command=self._apply_tracked_changes,
            state="disabled",
            width=150,
        )
        self._track_btn.pack(side="left", padx=(0, 8))
        ctk.CTkButton(toolbar, text="TXT", command=self._export_txt, width=60).pack(
            side="left", padx=(0, 4)
        )
        ctk.CTkButton(toolbar, text="CSV", command=self._export_csv, width=60).pack(
            side="left", padx=(0, 4)
        )
        ctk.CTkButton(
            toolbar, text="Spara båda", command=self._export_both, width=100
        ).pack(side="left", padx=(0, 8))
        ctk.CTkButton(
            toolbar,
            text="Rensa",
            command=self._clear_results,
            width=70,
            fg_color="transparent",
            text_color=("#ff3b30", "#ff453a"),  # iOS red
            hover_color=("#ffeceb", "#3a1c1c"),
            border_width=1,
            border_color=("#ff3b30", "#ff453a"),
        ).pack(side="right")

        # Results textbox
        self._results = ctk.CTkTextbox(
            main, font=self._font_mono, state="disabled", wrap="none"
        )
        self._results.grid(row=1, column=0, sticky="nsew", padx=12, pady=(4, 12))

    # ------------------------------------------------------------------
    # Dynamic options panel
    # ------------------------------------------------------------------

    def _on_tool_changed(self, *_args):
        """Show/hide tool-specific options based on the selected tool."""
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

        if hasattr(self, "_run_btn"):
            if tool == "pdf2docx":
                self._run_btn.configure(text="▶  Konvertera")
            else:
                self._run_btn.configure(text="▶  Kör analys")

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
            # Show truncated filename
            name = os.path.basename(path)
            if len(name) > 35:
                name = name[:32] + "..."
            self._file_label.configure(text=name, text_color=("black", "white"))

    # ------------------------------------------------------------------
    # Analysis
    # ------------------------------------------------------------------

    def _update_progress(self, value: float):
        """Update progress bar (0.0 to 1.0). Thread-safe via self.after()."""
        self.after(0, lambda: self._progress.set(value))

    def _run_pdf_conversion(self):
        """Handle PDF to DOCX conversion."""
        if not self._filepath:
            messagebox.showerror("Ingen fil vald", "Välj en PDF-fil först.")
            return
        if not self._filepath.lower().endswith(".pdf"):
            messagebox.showerror("Fel filtyp", "Välj en PDF-fil för konvertering.")
            return

        # Ask for save location
        base = os.path.basename(self._filepath)
        name, _ = os.path.splitext(base)
        default_name = f"{name}.docx"

        dst_path = filedialog.asksaveasfilename(
            title="Spara DOCX-fil",
            defaultextension=".docx",
            initialfile=default_name,
            filetypes=[("Word-dokument", "*.docx"), ("Alla filer", "*.*")],
        )
        if not dst_path:
            return

        self._run_btn.configure(state="disabled")
        self._status_label.configure(text="Konverterar...")
        self._progress.set(0)
        self._progress.pack(fill="x", pady=(0, 4))

        def _worker():
            import time

            start = time.perf_counter()
            try:
                from src.tools.pdf_converter import convert_pdf_to_docx

                result = convert_pdf_to_docx(
                    self._filepath,
                    dst_path,
                    progress_callback=self._update_progress,
                )
                elapsed = time.perf_counter() - start
                output = (
                    f"✅ Konvertering klar! ({elapsed:.1f}s)\n\n"
                    f"Sidor: {result['pages']}\n"
                    f"Sparad som: {dst_path}\n"
                )
                self._post_results(output, [], None, None, None, 1, elapsed)
                self.after(
                    0,
                    lambda: messagebox.showinfo(
                        "Konvertering klar",
                        f"PDF konverterad till DOCX:\n{dst_path}",
                    ),
                )
            except Exception as exc:
                elapsed = time.perf_counter() - start
                self._post_results(
                    f"❌ Fel vid konvertering:\n{exc}\n",
                    [],
                    None,
                    None,
                    None,
                    0,
                    elapsed,
                )

        thread = threading.Thread(target=_worker, daemon=True)
        thread.start()

    def _run_analysis(self):
        """Validate input and launch analysis in a background thread."""
        if not self._filepath:
            messagebox.showerror("Ingen fil vald", "Välj en fil innan du kör analysen.")
            return

        if self._tool_var.get() == "pdf2docx":
            self._run_pdf_conversion()
            return

        self._run_btn.configure(state="disabled")
        self._status_label.configure(text="Analyserar...")

        if self._tool_var.get() == "spell":
            self._progress.set(0)
            self._progress.pack(fill="x", pady=(0, 4))

        thread = threading.Thread(target=self._analyse_worker, daemon=True)
        thread.start()

    def _analyse_worker(self):
        """Run the selected tool in a background thread."""
        start = time.perf_counter()
        findings: list = []
        freq_result: dict | None = None
        sentence_stats: dict | None = None
        output: str = ""
        tool = self._tool_var.get()
        tool_name = TOOL_NAMES.get(tool, tool)

        try:
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

                result = spell_check(
                    text,
                    lang=self._lang_var.get(),
                    progress_callback=self._update_progress,
                    status_callback=lambda msg: self.after(
                        0, lambda: self._status_label.configure(text=msg)
                    ),
                )
                findings.extend(result["findings"])
                output = self._format_spell_results(result)

            elif tool == "typo":
                from src.tools.typo_checker import check as typo_check
                from src.tools.typo_checker import fix as typo_fix

                result = typo_check(text)
                findings.extend(result)
                output = self._format_findings("Typografiska fel", result)

                fix_result = typo_fix(text)
                self._fix_data = {"filepath": self._filepath, "result": fix_result}

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

        except Exception as exc:
            output = f"=== {tool_name} ===\nFel: {exc}\n"

        elapsed = time.perf_counter() - start
        total_findings = len(findings)
        if freq_result is not None:
            count_label = f"{freq_result.get('unique_words', 0)} unika ord"
        elif tool == "spell":
            count_label = f"{len(result['grouped'])} unika ord, {len(result['findings'])} förekomster"
        else:
            count_label = f"{total_findings} fynd"
        summary = f"Analys klar: {tool_name} — {count_label}. ({elapsed:.1f}s)\n\n"
        full_text = summary + output

        self._post_results(
            full_text, findings, freq_result, sentence_stats, None, 1, elapsed
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
        self.after(0, lambda: self._update_results_ui(text))

    def _update_results_ui(self, text: str):
        """Update the results text area and re-enable the run button."""
        self._results.configure(state="normal")
        self._results.delete("0.0", "end")
        self._results.insert("0.0", text)
        self._results.configure(state="disabled")
        self._run_btn.configure(state="normal")
        self._status_label.configure(text="")
        self._progress.pack_forget()
        if self._fix_data and self._fix_data["result"]["changes"]:
            self._fix_btn.configure(state="normal")
        else:
            self._fix_btn.configure(state="disabled")
        if (
            self._filepath.lower().endswith(".docx")
            and self._tool_var.get() == "typo"
            and self._findings
        ):
            self._track_btn.configure(state="normal")
        else:
            self._track_btn.configure(state="disabled")

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

    def _format_spell_results(self, result: dict) -> str:
        """Format spell check results as a grouped table."""
        grouped = result["grouped"]
        all_findings = result["findings"]
        total_occ = len(all_findings)
        unique = len(grouped)

        lines: list[str] = []
        lines.append(
            f"=== Stavningskontroll ({unique} unika ord, {total_occ} totala förekomster) ==="
        )
        lines.append("")

        if not grouped:
            lines.append("Inga stavfel hittades.")
            lines.append("")
            return "\n".join(lines)

        word_width = max(len(g["word"]) for g in grouped)
        word_width = max(word_width, 3) + 2

        header = (
            f"  {'#':>3}   {'Ord':<{word_width}} {'Antal':>5}   "
            f"{'Rader':<20} {'Förslag'}"
        )
        lines.append(header)
        lines.append("─" * max(len(header), 60))

        for rank, g in enumerate(grouped, start=1):
            line_nums = g["lines"]
            if len(line_nums) > 5:
                lines_str = ", ".join(str(n) for n in line_nums[:5]) + ", ..."
            else:
                lines_str = ", ".join(str(n) for n in line_nums)

            suggestions_str = ", ".join(g["suggestions"]) if g["suggestions"] else "—"

            lines.append(
                f"  {rank:>3}   {g['word']:<{word_width}} {g['count']:>5}   "
                f"{lines_str:<20} {suggestions_str}"
            )

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

        max_count = max((c for _, c in distribution), default=1) or 1
        max_bar = 20

        lines.append("Fördelning:")
        for label, count in distribution:
            bar_len = round(count / max_count * max_bar) if count > 0 else 0
            bar = "█" * bar_len if bar_len > 0 else "░"
            lines.append(f"  {label + ' ord':<12} {bar} {count}")
        lines.append("")

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

    # ------------------------------------------------------------------
    # Results area controls
    # ------------------------------------------------------------------

    def _clear_results(self):
        self._results_text = ""
        self._findings = []
        self._freq_result = None
        self._sentence_stats = None
        self._fix_data = None
        self._fix_btn.configure(state="disabled")
        self._track_btn.configure(state="disabled")
        self._results.configure(state="normal")
        self._results.delete("0.0", "end")
        self._results.configure(state="disabled")

    # ------------------------------------------------------------------
    # Auto-fix preview
    # ------------------------------------------------------------------

    def _autofix(self):
        """Open a preview window showing proposed typo fixes."""
        if not self._fix_data:
            return

        fix_result = self._fix_data["result"]
        changes = fix_result["changes"]
        fixed_text = fix_result["fixed_text"]

        win = ctk.CTkToplevel(self)
        win.title("Förhandsgranskning av ändringar")
        win.minsize(600, 400)

        # Preview textbox
        preview = ctk.CTkTextbox(win, font=self._font_mono, wrap="word", state="normal")
        preview.pack(fill="both", expand=True, padx=12, pady=(12, 4))

        for ch in changes:
            preview.insert("end", f"Rad {ch['line']}:\n")
            preview.insert("end", f'  Före:  "{ch["before"]}"\n')
            preview.insert("end", f'  Efter: "{ch["after"]}"\n\n')

        preview.insert("end", f"{len(changes)} rader ändrade\n")
        preview.configure(state="disabled")

        # Buttons
        btn_frame = ctk.CTkFrame(win, fg_color="transparent")
        btn_frame.pack(fill="x", padx=12, pady=(4, 12))

        def _save_fixed():
            from src.tools.typo_checker import fix_docx as typo_fix_docx

            base = os.path.basename(self._fix_data["filepath"])
            name, ext = os.path.splitext(base)

            if ext.lower() == ".docx":
                default_name = f"{name}_fixed.docx"
                path = filedialog.asksaveasfilename(
                    title="Spara fixad fil",
                    defaultextension=".docx",
                    initialfile=default_name,
                    filetypes=[("Word-dokument", "*.docx"), ("Alla filer", "*.*")],
                )
                if path:
                    try:
                        typo_fix_docx(self._fix_data["filepath"], path)
                        messagebox.showinfo("Sparat", f"Fixad fil sparad:\n{path}")
                        win.destroy()
                    except Exception as exc:
                        messagebox.showerror("Fel vid sparning", str(exc))
            else:
                default_name = f"{name}_fixed.txt"
                path = filedialog.asksaveasfilename(
                    title="Spara fixad fil",
                    defaultextension=".txt",
                    initialfile=default_name,
                    filetypes=[("Textfil", "*.txt"), ("Alla filer", "*.*")],
                )
                if path:
                    try:
                        with open(path, "w", encoding="utf-8") as fh:
                            fh.write(fixed_text)
                        messagebox.showinfo("Sparat", f"Fixad fil sparad:\n{path}")
                        win.destroy()
                    except Exception as exc:
                        messagebox.showerror("Fel vid sparning", str(exc))

        ctk.CTkButton(btn_frame, text="Spara som ny fil", command=_save_fixed).pack(
            side="left", padx=(0, 6)
        )
        ctk.CTkButton(btn_frame, text="Avbryt", command=win.destroy).pack(side="left")

    # ------------------------------------------------------------------
    # Apply tracked changes to DOCX
    # ------------------------------------------------------------------

    def _apply_tracked_changes(self):
        """Apply typo fixes as tracked changes to a copy of the source DOCX."""
        from src.tools.tracked_changes import fix_docx_tracked

        if not self._filepath or not self._findings:
            return

        base = os.path.basename(self._filepath)
        name, _ = os.path.splitext(base)
        default_name = f"{name}_tracked.docx"

        path = filedialog.asksaveasfilename(
            title="Spara DOCX med spårade ändringar",
            defaultextension=".docx",
            initialfile=default_name,
            filetypes=[("Word-dokument", "*.docx"), ("Alla filer", "*.*")],
        )
        if not path:
            return

        try:
            author = self._author_var.get().strip() or "Editing Tools"
            changes = fix_docx_tracked(self._filepath, path, author=author)
            messagebox.showinfo(
                "Spårade ändringar",
                f"{len(changes)} ändringar sparade som spårade ändringar i:\n{path}",
            )
        except Exception as exc:
            messagebox.showerror("Fel", str(exc))

    # ------------------------------------------------------------------
    # Export
    # ------------------------------------------------------------------

    def _stem(self) -> str:
        """Derive a base name from the loaded file path."""
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

                if self._findings:
                    writer.writerow(
                        ["verktyg", "rad", "kolumn", "beskrivning", "utdrag"]
                    )
                    for f in self._findings:
                        writer.writerow(
                            [f.tool, f.line_number, f.column, f.description, f.excerpt]
                        )

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
