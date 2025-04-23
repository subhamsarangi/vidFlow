uvicorn main:app --reload --host 0.0.0.0

FIXING ERRORS:
netstat -ano | findstr :8000
taskkill /PID <PID> /F

192.168.29.76:8000