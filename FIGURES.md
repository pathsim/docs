# Figures and diagrams in docstrings

The API reference is generated from the Python docstrings of each package
(`scripts/build.py` -> griffe -> docutils -> HTML). Docstrings can include
figures and diagrams in two ways. Both feed into the per-version
`static/{package}/{tag}/figures/` directory that the docs site serves.

## 1. Referenced figures

Use the standard RST `.. figure::` / `.. image::` directive with the figure's
filename. The file is looked up by name in the package's central figure roots
(anything under `docs/source/`, e.g. `docs/source/figures/`), so you only give
the basename:

```rst
.. figure:: block_diagram.png
   :width: 400

   The integrator block.
```

At build time the file is:

- **resolved** against the package figure roots,
- **re-encoded to WebP** (raster formats; SVG is passed through unchanged) so
  the site stays fast,
- **collected** into the served figures directory, and
- the `<img>` `src` is rewritten to the versioned path.

A missing figure is logged as a warning and left as-is; it never breaks the
build.

## 2. Inline TikZ diagrams

Write TikZ directly in the docstring with a `.. tikz::` block. The body is
either a full `tikzpicture` environment or just bare drawing commands (which are
wrapped automatically):

```rst
.. tikz::

   \draw[->] (-0.2,0) -- (2.2,0) node[right] {$t$};
   \draw[->] (0,-0.2) -- (0,1.6) node[above] {$y$};
   \draw[thick] (0,0) .. controls (1,1.6) .. (2,1);
```

At build time each block is:

- **compiled to SVG** (tectonic in CI, pdflatex/lualatex locally),
- **content-hash cached** so unchanged diagrams are not recompiled,
- **inlined** into the page so it loads without an extra request, and
- **themed**: pure-black strokes/fills become `currentColor`, so diagrams stay
  legible in both light and dark mode.

If the LaTeX toolchain is unavailable the block **degrades to a code listing**
of its source rather than breaking the build.

### Local toolchain

To render TikZ locally you need a LaTeX engine and a PDF->SVG converter:

- engine: `tectonic`, `lualatex` or `pdflatex` (e.g. MiKTeX on Windows),
- converter: `dvisvgm`, `pdftocairo` or `pdf2svg`.

CI installs `tectonic` + `dvisvgm` automatically (see `deploy.yml`).

### Custom preamble

A package may override the default TikZ preamble (extra libraries, styles) by
adding `docs/source/tikz_preamble.tex`.

## Image optimization

All raster images that reach the served tree (referenced figures, notebook
figures, and executed-notebook outputs) are re-encoded to WebP at build time.
SVGs are kept as vectors. Tunables live in `scripts/lib/config.py`
(`WEBP_QUALITY`, `WEBP_METHOD`, ...).
