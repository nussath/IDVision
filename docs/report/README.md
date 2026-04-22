# IDVision — Project Report

LaTeX source and compiled PDF of the MCA 2024–26 project report.

## Files

- `ind_report.tex` — main LaTeX source
- `ind_report.pdf` — last compiled build
- `*.png` — all figures and screenshots referenced by the report
  (architecture and workflow diagrams are now drawn with TikZ and live
  inline in `ind_report.tex`, so there is no `architecture.png` or
  `Untitled diagram.png` anymore)

## Rebuild

```bash
pdflatex ind_report.tex
pdflatex ind_report.tex
```

Two passes are needed so the table of contents, list of figures, and
cross-references resolve. TikZ libraries (`arrows.meta`, `positioning`,
`shapes.geometric`, `calc`, `fit`) ship with any standard TeX Live or
MiKTeX distribution, no extra install required.
