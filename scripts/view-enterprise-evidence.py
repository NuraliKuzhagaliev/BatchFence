"""Loopback viewer for retained synthetic evidence. New model requests disabled."""
import json,os,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
profile=sys.argv[1];assert profile in ('receiving-v2','frozen')
folder=ROOT/'work'/('enterprise-live-v2' if profile=='receiving-v2' else 'enterprise-live-frozen')
port=8796 if profile=='receiving-v2' else 8797
private=json.loads((folder/'private.json').read_text())
os.environ.update(DATABASE_PATH=str(folder/'state.sqlite3'),SOURCE_STORAGE_PATH=str(folder/'sources'),DEPLOYMENT_PROFILE='pilot',
    PILOT_DATABASE_URL='',PILOT_SESSION_SECRET=private['session_secret'],PILOT_AMD_DATA_APPROVED='false',PUBLIC_DEMO='false',
    APP_ORIGIN=f'http://127.0.0.1:{port}',INFERENCE_MODE='fixture')
import uvicorn
uvicorn.run('backend.app:app',host='127.0.0.1',port=port)
