$env:KMP_DUPLICATE_LIB_OK="TRUE"
$env:OMP_NUM_THREADS="1"
$env:MKL_NUM_THREADS="1"

.\venv\Scripts\python.exe -m uvicorn main:app --reload --port 8765
