@echo off
set KMP_DUPLICATE_LIB_OK=TRUE
set OMP_NUM_THREADS=1
set MKL_NUM_THREADS=1

.\venv\Scripts\python.exe -m uvicorn main:app --reload --port 8765
