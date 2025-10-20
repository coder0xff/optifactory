@echo off
echo Cleaning up previous coverage data...
del /f /q .coverage* 2>nul
echo Running pytest with coverage...
python -m coverage run --source=. -m pytest
echo.
echo Generating coverage reports...
python -m coverage html
python -m coverage report --show-missing
echo.
echo Coverage report generated in htmlcov\index.html

