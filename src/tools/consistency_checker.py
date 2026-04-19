import re

from .models import Finding

TOOL_NAME = "consistency_checker"

VARIANT_GROUPS: list[set[str]] = [
    # ── Abbreviations vs full forms ──────────────────────────────────────
    {"t.ex.", "t ex", "t.ex", "tex", "till exempel"},
    {"bl.a.", "bl a", "bl.a", "bland annat"},
    {"dvs.", "dvs", "d.v.s.", "d.v.s", "det vill säga"},
    {"osv.", "osv", "o.s.v.", "och så vidare"},
    {"m.m.", "m m", "med mera"},
    {"m.fl.", "m fl", "med flera"},
    {"s.k.", "s k", "s.k", "så kallad", "så kallade", "så kallat"},
    {"f.d.", "f d", "f.d", "före detta"},
    {"t.o.m.", "t o m", "till och med"},
    {"f.ö.", "f ö", "för övrigt"},
    {"o.d.", "o d", "och dylikt"},
    {"ev.", "ev", "eventuellt", "eventuella"},
    {"ca.", "ca", "cirka", "ungefär"},
    {"resp.", "resp", "respektive"},
    {"enl.", "enl", "enligt"},
    {"nr.", "nr", "nummer"},
    {"st.", "st", "stycken"},
    {"kl.", "kl", "klockan"},
    {"pga.", "pga", "p.g.a.", "p.g.a", "på grund av"},
    {"ang.", "ang", "angående"},
    {"avd.", "avd", "avdelning"},
    {"tel.", "tel", "telefon"},
    {"forts.", "forts", "fortsättning"},
    {"obs.", "obs", "observera"},
    {"max.", "max", "maximum", "maximalt"},
    {"min.", "min", "minimum", "minimalt"},
    {"inkl.", "inkl", "inklusive"},
    {"exkl.", "exkl", "exklusive"},
    {"ref.", "ref", "referens"},
    {"spec.", "spec", "specifikation"},
    {"info.", "info", "information"},
    {"org.", "org", "organisation"},
    {"avg.", "avg", "avgift"},
    {"ber.", "ber", "beräknad", "beräknat"},
    {"dept.", "dept", "departement"},
    # ── Swedish/English variants ─────────────────────────────────────────
    {"e-post", "epost", "email", "e-mail", "mejl"},
    {"webb", "web"},
    {"webbplats", "webbsida", "hemsida", "website"},
    {"dator", "computer"},
    {"mjukvara", "programvara", "software"},
    {"hårdvara", "hardware"},
    {"mobiltelefon", "mobil", "smartphone"},
    {"internet", "Internet", "nätet"},
    {"online", "på nätet", "på webben"},
    {"app", "applikation", "application"},
    {"feedback", "återkoppling"},
    {"deadline", "tidsfrist", "slutdatum"},
    {"möte", "meeting"},
    {"team", "lag", "grupp"},
    {"chef", "manager"},
    {"projekt", "project"},
    {"dokument", "document"},
    {"server", "servern", "tjänstedator"},
    {"backup", "säkerhetskopia", "säkerhetskopiering"},
    {"password", "lösenord"},
    {"username", "användarnamn"},
    {"login", "inloggning"},
    {"logout", "utloggning"},
    {"download", "nedladdning", "ladda ner"},
    {"upload", "uppladdning", "ladda upp"},
    {"update", "uppdatering"},
    {"interface", "gränssnitt"},
    {"browser", "webbläsare"},
    {"link", "länk"},
    {"file", "fil"},
    {"folder", "mapp", "katalog"},
    {"feature", "funktion", "funktionalitet"},
    {"bug", "bugg", "fel", "programfel"},
    {"patch", "programfix"},
    {"sprint", "iteration"},
    {"standup", "stand-up", "morgonmöte"},
    {"workshop", "verkstad", "arbetsträff"},
    {"brainstorm", "brainstorming", "idéstorm"},
    {"stakeholder", "intressent"},
    {"roadmap", "färdplan"},
    {"scope", "omfattning"},
    {"deploy", "driftsätta", "driftsättning"},
    {"release", "utgåva", "version"},
    {"branch", "gren"},
    {"merge", "sammanfoga"},
    {"review", "granskning"},
    {"refactor", "refaktorisera", "omstrukturera"},
    {"template", "mall"},
    {"default", "standard", "förval"},
    {"dashboard", "instrumentpanel", "översiktssida"},
    {"cookie", "kaka"},
    # ── Spelling variants ────────────────────────────────────────────────
    {"i dag", "idag"},
    {"i morgon", "imorgon"},
    {"i kväll", "ikväll"},
    {"i går", "igår"},
    {"i bland", "ibland"},
    {"e-bok", "ebok"},
    {"e-handel", "ehandel"},
    {"e-tjänst", "etjänst"},
    {"e-legitimation", "elegitimation"},
    {"varandra", "var andra"},
    {"någon gång", "någongång"},
    {"ingen ting", "ingenting"},
    {"alla fall", "allfall", "i alla fall", "iaf"},
    {"till sammans", "tillsammans"},
    {"över huvud taget", "överhuvudtaget"},
    {"för utom", "förutom"},
    {"efter som", "eftersom"},
    {"även om", "ävenom"},
    {"framför allt", "framförallt"},
    {"så väl", "såväl"},
    {"så som", "såsom"},
    {"över allt", "överallt"},
    # ── Number/format variants ───────────────────────────────────────────
    {"procent", "%", "pct"},
    {"grader", "°"},
    {"kronor", "kr", "SEK"},
    {"euro", "€", "EUR"},
    {"dollar", "$", "USD"},
    {"tusen", "1000", "1 000"},
    {"miljon", "miljoner", "mn", "mnkr"},
    {"miljard", "miljarder", "md", "mdkr"},
    # ── Punctuation style variants ───────────────────────────────────────
    {"\u201c", "\u201d", "\u00bb", "\u00ab"},  # " " » «  — quotation mark styles
    {"\u2013", "\u2014", " - "},  # – — and spaced hyphen
    # ── Title/honorific variants ─────────────────────────────────────────
    {"herr", "hr", "hr.", "Mr", "Mr."},
    {"fru", "fru.", "Mrs", "Mrs."},
    {"doktor", "dr", "dr.", "Dr", "Dr."},
    {"professor", "prof", "prof.", "Prof", "Prof."},
    # ── Common Swedish style choices ─────────────────────────────────────
    {"ska", "skall"},
    {"ej", "inte", "icke"},
    {"dock", "emellertid", "likväl"},
    {"men", "dock"},
    {"eller", "alternativt"},
    {"sedan", "sen"},
    {"någon", "nån"},
    {"något", "nåt"},
    {"några", "nåra"},
    {"sådant", "sånt"},
    {"mycket", "väldigt", "jätte-"},
]


def _build_pattern(variant: str) -> re.Pattern[str]:
    """Build a regex pattern for a variant.

    Short variants and single words use word boundaries.
    Multi-word phrases and variants containing punctuation/symbols are
    searched as literal substrings.
    """
    escaped = re.escape(variant)

    # Punctuation-only or symbol variants (%, °, €, $, quotes, dashes)
    if re.fullmatch(r"[^\w\s]+", variant):
        return re.compile(re.escape(variant))

    # Multi-word phrases: literal case-insensitive substring
    if " " in variant:
        return re.compile(escaped, re.IGNORECASE)

    # Variants ending with a dot (abbreviations like "t.ex."): word boundary
    # only on the left side, the dot naturally terminates on the right.
    if variant.endswith("."):
        return re.compile(r"(?<!\w)" + escaped, re.IGNORECASE)

    # Single tokens — use word boundaries
    return re.compile(r"\b" + escaped + r"\b", re.IGNORECASE)


def _excerpt(line_text: str, start: int, length: int, max_len: int = 60) -> str:
    """Extract an excerpt around the match, at most max_len characters."""
    # We want to center the match in the excerpt
    margin = (max_len - length) // 2
    excerpt_start = max(0, start - margin)
    excerpt_end = min(len(line_text), start + length + margin)
    snippet = line_text[excerpt_start:excerpt_end].strip()
    prefix = "…" if excerpt_start > 0 else ""
    suffix = "…" if excerpt_end < len(line_text) else ""
    return f"{prefix}{snippet}{suffix}"


def check(text: str) -> list[Finding]:
    """Flag inconsistent usage of variant words/phrases in the text."""
    lines = text.split("\n")
    text_lower = text.lower()

    findings: list[Finding] = []

    for group in VARIANT_GROUPS:
        # Phase 1: determine which variants are present at all
        present: dict[str, re.Pattern[str]] = {}
        for variant in group:
            pattern = _build_pattern(variant)
            # Quick presence check (case-insensitive for text, pattern already
            # handles it, but we do a fast pre-filter for non-regex variants)
            if pattern.search(text):
                present[variant] = pattern

        if len(present) < 2:
            continue

        # Phase 2: collect all occurrences, deduplicate overlapping matches
        all_matches: list[tuple[int, int, int, str]] = []
        for variant, pattern in present.items():
            for line_idx, line in enumerate(lines):
                for m in pattern.finditer(line):
                    all_matches.append((line_idx, m.start(), m.end(), variant))

        # Remove matches that are subsumed by a longer match at the same
        # position (e.g. "t.ex" inside "t.ex." at the same start).
        all_matches.sort(key=lambda x: (x[0], x[1], -(x[2] - x[1])))
        filtered: list[tuple[int, int, int, str]] = []
        for match in all_matches:
            line_idx, start, end, variant = match
            # Check if a longer match already covers this span
            subsumed = False
            for f_line, f_start, f_end, _ in filtered:
                if (
                    f_line == line_idx
                    and f_start <= start
                    and f_end >= end
                    and (f_end - f_start) > (end - start)
                ):
                    subsumed = True
                    break
            if not subsumed:
                filtered.append(match)

        # Recompute actually-found variants after filtering
        filtered_variants = {v for _, _, _, v in filtered}
        if len(filtered_variants) < 2:
            continue

        for line_idx, start, end, variant in filtered:
            others = filtered_variants - {variant}
            others_str = "', '".join(sorted(others))
            matched_text = lines[line_idx][start:end]
            exc = _excerpt(lines[line_idx], start, len(matched_text))
            findings.append(
                Finding(
                    tool=TOOL_NAME,
                    line_number=line_idx + 1,
                    column=start + 1,
                    description=(
                        f"Inkonsekvent användning: '{matched_text}' "
                        f"(även '{others_str}' förekommer i texten)"
                    ),
                    excerpt=exc,
                )
            )

    findings.sort(key=lambda f: (f.line_number, f.column))
    return findings
