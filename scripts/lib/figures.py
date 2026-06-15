"""
Docstring figure + diagram support for the API reference build.

Two capabilities, both funnelling into the per-version ``figures/`` directory so
the frontend can serve them like any other figure:

1. **Figure references** — a docstring may use the standard RST ``.. figure::``
   / ``.. image:: name.png`` directive. The referenced file is looked up in the
   package's central figure roots (e.g. ``docs/source/figures``), optimized to
   WebP (SVG passed through), and the ``<img src>`` rewritten to the served
   ``{package}/{tag}/figures/...`` path.

2. **TikZ diagrams** — a docstring may carry a ``.. tikz::`` block whose body is
   TikZ source. It is compiled to SVG at build time (tectonic in CI, pdflatex /
   lualatex locally), saved into the figures directory and referenced by
   ``<img>`` like any other figure. Results are cached by content hash so
   unchanged diagrams are not recompiled on the 6-hourly rebuilds.

The :class:`FigureCollector` is created once per (package, tag) and threaded
through the API extractor. If the LaTeX toolchain is missing the TikZ block
degrades to a code block rather than breaking the build.
"""

from __future__ import annotations

import hashlib
import re
import shutil
import subprocess
from pathlib import Path

from .config import (
    TIKZ_COLOR,
    TIKZ_EM_PER_PT,
    TIKZ_GLYPH_STROKE_PT,
    TIKZ_LATEX_ENGINES,
    TIKZ_PDF_TO_SVG,
    TIKZ_TIMEOUT,
)
from .images import optimize_image

# Image extensions we resolve from the package figure roots.
_IMAGE_GLOBS = ["*.png", "*.jpg", "*.jpeg", "*.svg", "*.gif"]

# Default standalone-document preamble for TikZ compilation. A package can
# override it with docs/source/tikz_preamble.tex.
DEFAULT_TIKZ_PREAMBLE = r"""
\usepackage{tikz}
\usepackage{amsmath}
\usetikzlibrary{arrows.meta,positioning,calc,shapes.geometric,backgrounds,fit,decorations.pathmorphing}
% Bolder defaults so diagrams read well at docs scale: thicker lines, larger font.
\tikzset{every picture/.style={line width=0.7pt, font=\large}}
"""


class FigureCollector:
    """Resolve, render and collect docstring figures for one (package, tag)."""

    def __init__(
        self,
        package_id: str,
        tag: str,
        figures_dir: Path,
        source_roots: list[Path],
        cache_dir: Path,
        tikz_preamble: str = DEFAULT_TIKZ_PREAMBLE,
    ):
        self.package_id = package_id
        self.tag = tag
        self.figures_dir = Path(figures_dir)
        self.cache_dir = Path(cache_dir)
        self.tikz_preamble = tikz_preamble
        self.web_prefix = f"{package_id}/{tag}/figures"

        # Lazily-built basename -> source path index over the figure roots.
        self._index: dict[str, Path] | None = None
        self._source_roots = [Path(r) for r in source_roots if Path(r).exists()]

        # Resolved toolchain (None until probed; False if unavailable).
        self._engine: str | None | bool = None
        self._converter: str | None | bool = None

        # Per-build warning de-dup.
        self._missing: set[str] = set()
        self.tikz_rendered = 0
        self.tikz_failed = 0

    # ------------------------------------------------------------------ index

    def _build_index(self) -> dict[str, Path]:
        index: dict[str, Path] = {}
        for root in self._source_roots:
            for glob in _IMAGE_GLOBS:
                for path in root.rglob(glob):
                    index.setdefault(path.name.lower(), path)
        return index

    @property
    def index(self) -> dict[str, Path]:
        if self._index is None:
            self._index = self._build_index()
        return self._index

    # ----------------------------------------------------------- RST pre-pass

    def preprocess_rst(self, rst: str, source_file: Path | None = None) -> str:
        """Replace ``.. tikz::`` blocks with rendered ``.. image::`` references."""
        if ".. tikz::" not in rst:
            return rst
        return _replace_tikz_blocks(rst, self._render_tikz_block)

    def _render_tikz_block(self, code: str, indent: str) -> str:
        """Render one TikZ block; return replacement RST (image ref or fallback)."""
        rel = self.render_tikz(code)
        if rel:
            self.tikz_rendered += 1
            # Size font-relative (em) from the SVG's intrinsic pt width, so the
            # diagram scales with the surrounding text rather than the column.
            width_em = self._svg_width_em(self.figures_dir / rel)
            width_opt = f"\n{indent}   :width: {width_em:.2f}em" if width_em else ""
            return f"{indent}.. image:: {rel}\n{indent}   :class: tikz-figure{width_opt}\n"
        # Degrade gracefully: show the source instead of breaking the build.
        self.tikz_failed += 1
        body = "\n".join(f"{indent}   {line}" for line in code.splitlines())
        return f"{indent}.. code-block:: latex\n\n{body}\n"

    @staticmethod
    def _svg_width_em(svg_path: Path) -> float | None:
        """Read an SVG's intrinsic pt width and convert it to em (font-relative)."""
        try:
            head = svg_path.read_text(encoding="utf-8", errors="replace")[:400]
        except OSError:
            return None
        m = re.search(r"<svg\b[^>]*?\bwidth=['\"]([0-9.]+)pt['\"]", head)
        if not m:
            return None
        return float(m.group(1)) * TIKZ_EM_PER_PT

    # -------------------------------------------------------------- HTML pass

    def process_html(self, html: str, source_file: Path | None = None) -> str:
        """Resolve, collect and rewrite figure paths in docstring HTML.

        docutils renders SVG images as ``<object data=...>`` and raster images as
        ``<img src=...>``. We normalize the former to ``<img>`` (uniform handling,
        lazy-loadable, covered by the frontend base-path rewrite), then resolve
        every ``src`` against the figure roots.
        """
        if "<object" in html:
            html = self._objects_to_img(html)

        if "<img" not in html:
            return html

        def repl(match: re.Match) -> str:
            src = match.group("src")
            new = self._resolve_src(src)
            if new is None or new == src:
                return match.group(0)
            # Rewrite only the captured src value, never the surrounding tag
            # (alt="" often repeats the filename and must stay untouched).
            return match.group("pre") + new + match.group("post")

        return re.sub(
            r'(?P<pre><img[^>]*?\ssrc=["\'])(?P<src>[^"\']+)(?P<post>["\'])',
            repl,
            html,
        )

    def _objects_to_img(self, html: str) -> str:
        """Convert docutils SVG ``<object data=...>`` tags into ``<img src=...>``."""

        def conv(match: re.Match) -> str:
            tag = match.group(0)
            data = re.search(r'\bdata=["\']([^"\']+)["\']', tag)
            if not data:
                return tag
            # Carry over the attributes docutils put on the <object> so per-diagram
            # sizing (style/width/height) and the class survive the conversion.
            attrs = ""
            for name in ("class", "style", "width", "height"):
                a = re.search(rf'\b{name}=(["\'])(.*?)\1', tag)
                if a:
                    attrs += f' {name}="{a.group(2)}"'
            return f'<img src="{data.group(1)}"{attrs} alt="" />'

        return re.sub(
            r'<object\b[^>]*\btype=["\']image/svg\+xml["\'][^>]*>.*?</object>',
            conv,
            html,
            flags=re.IGNORECASE | re.DOTALL,
        )

    def _resolve_src(self, src: str) -> str | None:
        # Leave absolute URLs / data URIs untouched.
        if re.match(r"^(https?:)?//|^data:|^mailto:", src):
            return None

        rel = src.lstrip("./").replace("\\", "/")

        # Already collected into figures_dir (e.g. a rendered TikZ svg).
        if (self.figures_dir / rel).exists():
            return f"{self.web_prefix}/{rel}"

        basename = rel.rsplit("/", 1)[-1]
        source = self.index.get(basename.lower())
        if source is None:
            if basename not in self._missing:
                self._missing.add(basename)
                print(f"      Warning: docstring figure not found: {basename}")
            return None

        served = optimize_image(source, self.figures_dir)
        return f"{self.web_prefix}/{served}"

    # ------------------------------------------------------------- TikZ render

    def render_tikz(self, code: str) -> str | None:
        """
        Compile TikZ ``code`` to an SVG file under figures_dir/tikz/, content-cached.

        The SVG is saved to disk and referenced by ``<img>`` like any other figure.
        Returns the figures-relative path (e.g. "tikz/<hash>.svg") or None if the
        toolchain is unavailable or compilation failed. A persistent cache keyed by
        content hash avoids recompiling unchanged diagrams on the 6-hourly rebuilds.
        """
        code = code.strip()
        # Color is part of the cache key so changing TIKZ_COLOR invalidates it.
        key = f"{self.tikz_preamble}\n{TIKZ_COLOR}\n{code}"
        digest = hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]
        rel = f"tikz/{digest}.svg"
        dest = self.figures_dir / rel
        if dest.exists():
            return rel

        # Persistent cross-build cache so unchanged diagrams are not recompiled.
        cached = self.cache_dir / f"{digest}.svg"
        if cached.exists():
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(cached, dest)
            return rel

        svg = self._compile_tikz(code)
        if svg is None:
            return None

        svg = _recolor_svg(svg, TIKZ_COLOR)
        svg = _embolden_glyphs(svg, TIKZ_COLOR, TIKZ_GLYPH_STROKE_PT)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(svg, encoding="utf-8")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        cached.write_text(svg, encoding="utf-8")
        return rel

    def _resolve_toolchain(self) -> tuple[str | None, str | None]:
        if self._engine is None:
            self._engine = next((e for e in TIKZ_LATEX_ENGINES if shutil.which(e)), False)
        if self._converter is None:
            self._converter = next((c for c in TIKZ_PDF_TO_SVG if shutil.which(c)), False)
        return (self._engine or None, self._converter or None)

    def _compile_tikz(self, code: str) -> str | None:
        engine, converter = self._resolve_toolchain()
        if not engine or not converter:
            print(f"      Warning: TikZ toolchain unavailable (engine={engine}, svg={converter}); "
                  f"diagram left as source")
            return None

        import tempfile

        # Authors may write either a full picture (\begin{tikzpicture}...) or just
        # bare drawing commands — wrap the latter for convenience.
        body = code
        if "\\begin{tikzpicture}" not in code and "\\tikz" not in code:
            body = f"\\begin{{tikzpicture}}\n{code}\n\\end{{tikzpicture}}"

        document = (
            "\\documentclass[tikz,border=2pt]{standalone}\n"
            f"{self.tikz_preamble}\n"
            "\\begin{document}\n"
            f"{body}\n"
            "\\end{document}\n"
        )

        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            (tmp / "fig.tex").write_text(document, encoding="utf-8")
            try:
                if not self._run_latex(engine, tmp):
                    return None
                return self._pdf_to_svg(converter, tmp / "fig.pdf")
            except Exception as e:
                print(f"      Warning: TikZ compile error: {e}")
                return None

    def _run_latex(self, engine: str, workdir: Path) -> bool:
        if engine == "tectonic":
            cmd = ["tectonic", "--outdir", str(workdir), "--keep-logs",
                   "--synctex=0", str(workdir / "fig.tex")]
        else:
            cmd = [engine, "-interaction=nonstopmode", "-halt-on-error",
                   "-output-directory", str(workdir), str(workdir / "fig.tex")]
        result = subprocess.run(
            cmd, cwd=workdir, capture_output=True, text=True, timeout=TIKZ_TIMEOUT
        )
        if not (workdir / "fig.pdf").exists():
            tail = (result.stdout or result.stderr or "").strip()[-600:]
            print(f"      Warning: LaTeX ({engine}) produced no PDF:\n{tail}")
            return False
        return True

    def _pdf_to_svg(self, converter: str, pdf: Path) -> str | None:
        out = pdf.with_suffix(".svg")
        if converter == "dvisvgm":
            cmd = ["dvisvgm", "--pdf", "--no-fonts", "--output=" + str(out), str(pdf)]
        elif converter == "pdftocairo":
            cmd = ["pdftocairo", "-svg", str(pdf), str(out)]
        else:  # pdf2svg
            cmd = ["pdf2svg", str(pdf), str(out)]
        subprocess.run(cmd, capture_output=True, text=True, timeout=TIKZ_TIMEOUT)
        if out.exists():
            return out.read_text(encoding="utf-8", errors="replace")
        print(f"      Warning: PDF->SVG ({converter}) produced no output")
        return None


# --------------------------------------------------------------------------- helpers


def _replace_tikz_blocks(rst: str, render) -> str:
    """
    Find ``.. tikz::`` directive blocks and replace them via ``render(code, indent)``.

    A block is the directive line, optional ``:option:`` lines, then an indented
    body (more indented than the directive marker), ending at the first line that
    is non-blank and indented at or below the marker.
    """
    lines = rst.splitlines()
    out: list[str] = []
    i = 0
    directive_re = re.compile(r"^(?P<indent>\s*)\.\.\s+tikz::\s*(?P<arg>.*)$")

    while i < len(lines):
        m = directive_re.match(lines[i])
        if not m:
            out.append(lines[i])
            i += 1
            continue

        indent = m.group("indent")
        marker_indent = len(indent)
        i += 1

        # Skip option lines (":key: value") immediately after the directive.
        while i < len(lines):
            stripped = lines[i].strip()
            if stripped.startswith(":") and stripped.count(":") >= 2:
                i += 1
            else:
                break

        # Skip a single blank separator line.
        while i < len(lines) and not lines[i].strip():
            i += 1

        # Collect the indented body.
        body: list[str] = []
        while i < len(lines):
            line = lines[i]
            if not line.strip():
                body.append("")
                i += 1
                continue
            cur_indent = len(line) - len(line.lstrip())
            if cur_indent <= marker_indent:
                break
            body.append(line)
            i += 1

        # Dedent the body to its minimum common indentation.
        non_empty = [b for b in body if b.strip()]
        common = min((len(b) - len(b.lstrip()) for b in non_empty), default=0)
        code = "\n".join(b[common:] if b.strip() else "" for b in body).strip("\n")

        out.append(render(code, indent))
        # Guarantee a blank line so the replacement block is not glued to the
        # paragraph that follows (the body loop consumes the original separator).
        out.append("")

    return "\n".join(out)


_BLACK = r"(?:#000000|#000|black|rgb\(0,\s*0,\s*0\))"


def _recolor_svg(svg: str, color: str) -> str:
    """Recolor black line art to ``color`` (background stays transparent).

    dvisvgm emits black line art on a transparent background. We swap black for
    the docs muted text color so diagrams blend into the prose:

    - **explicit** black strokes/fills (the drawn paths) are rewritten directly,
      both attribute form (``stroke='#000'``) and CSS form (``fill:#000000``);
    - text/math glyphs are emitted as ``<path>`` with *no* fill, so they fall
      back to the SVG default (black). Setting ``fill``/``color`` on the root
      ``<svg>`` makes those inherit the muted color, while explicitly stroked
      lines (``fill='none'``) are unaffected.
    """
    svg = re.sub(
        rf"\b(fill|stroke)=(['\"]){_BLACK}\2",
        lambda m: f'{m.group(1)}="{color}"',
        svg,
        flags=re.IGNORECASE,
    )
    svg = re.sub(
        rf"\b(fill|stroke):\s*{_BLACK}",
        lambda m: f"{m.group(1)}:{color}",
        svg,
        flags=re.IGNORECASE,
    )

    # Default color for glyph paths that carry no explicit fill.
    def _inject(match: re.Match) -> str:
        attrs = match.group(2)
        if re.search(r"\bfill=", attrs):
            return match.group(0)
        return f"{match.group(1)}{attrs} fill=\"{color}\"{match.group(3)}"

    svg = re.sub(r"(<svg\b)([^>]*?)(\s*>)", _inject, svg, count=1)
    return svg


def _embolden_glyphs(svg: str, color: str, width: float) -> str:
    """Add a hairline stroke to fill-only glyph paths so text matches KaTeX weight.

    Targets ``<path>`` elements that carry neither ``stroke=`` nor ``fill=`` (the
    outlined glyphs, which inherit the root fill). Drawn lines and box outlines
    already have an explicit ``stroke``/``fill`` and are left untouched.
    """
    if width <= 0:
        return svg

    def _add(match: re.Match) -> str:
        return (f'<path stroke="{color}" stroke-width="{width:g}" '
                f'stroke-linejoin="round"{match.group(1)}')

    # <path ...> with no stroke= and no fill= up to the closing '>'.
    return re.sub(r"<path\b(?![^>]*\b(?:stroke|fill)=)([^>]*>)", _add, svg)
