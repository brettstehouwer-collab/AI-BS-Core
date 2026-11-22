import sys
sys.path.insert(0, r'C:\AI-BS\backend')
import uvicorn

if __name__ == '__main__':
    uvicorn.run('app.main:app', host='0.0.0.0', port=8025, log_level='info')