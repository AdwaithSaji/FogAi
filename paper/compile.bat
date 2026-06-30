@echo off
:: ============================================================
::  FogAI Paper — Compile Script (Windows)
::  Requires: TeX Live or MiKTeX with IEEEtran class installed
::
::  Run this .bat from the paper\ directory:
::    cd paper
::    compile.bat
:: ============================================================

set BASENAME=fogai_icnccom2026

echo [1/4] pdflatex (first pass)...
pdflatex -interaction=nonstopmode %BASENAME%.tex
if errorlevel 1 goto :err

echo [2/4] bibtex (references)...
bibtex %BASENAME%
if errorlevel 1 goto :err

echo [3/4] pdflatex (second pass)...
pdflatex -interaction=nonstopmode %BASENAME%.tex

echo [4/4] pdflatex (third pass — final)...
pdflatex -interaction=nonstopmode %BASENAME%.tex

echo.
echo Done.  Output: %BASENAME%.pdf
pause
goto :eof

:err
echo.
echo *** Compile error — check %BASENAME%.log for details ***
pause
