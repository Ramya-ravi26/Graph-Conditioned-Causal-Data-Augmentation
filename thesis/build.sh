#!/usr/bin/env bash
# Build thesis/build/thesis.pdf (pdflatex + biber). Needs TeX Live with tuda-ci,
# biblatex/biber, pgfplots, algorithmicx and the XCharter/Roboto fonts
# (Ubuntu: texlive-latex-extra texlive-publishers texlive-bibtex-extra biber
#  texlive-pictures texlive-science texlive-lang-german texlive-fonts-extra).
# The TU Darmstadt logo (tuda_logo.pdf) is not part of TeX Live; place the
# official file in thesis/ -- otherwise a neutral placeholder is generated.
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p build
cp thesis.tex references.bib build/
if [ -f tuda_logo.pdf ]; then cp tuda_logo.pdf build/; else
  (cd build && printf '%s\n' '\documentclass{standalone}\begin{document}\rule{3cm}{1.2cm}\end{document}' > logo.tex \
     && pdflatex -interaction=nonstopmode logo.tex >/dev/null && mv logo.pdf tuda_logo.pdf)
fi
cd build
pdflatex -interaction=nonstopmode thesis.tex >/dev/null || true
biber thesis >/dev/null
pdflatex -interaction=nonstopmode thesis.tex >/dev/null || true
biber thesis >/dev/null
pdflatex -interaction=nonstopmode thesis.tex >/dev/null || true
pdflatex -interaction=nonstopmode thesis.tex > pdflatex.log || true
echo "errors:";             grep -c '^!' thesis.log || true
echo "undefined refs:";     grep -c 'undefined' thesis.log || true
echo "biber warnings:";     grep -c 'WARN' thesis.blg || true
ls -la thesis.pdf
