## FEATURES
- Chunked upload and reassemble
- Partial Streaming
- Hotlinking protection

## RUN
`uvicorn main:app --reload --host 0.0.0.0`

## FIXING ERRORS:
- `netstat -ano | findstr :8000`

- `taskkill /PID <PID> /F`