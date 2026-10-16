"""Single-instance deployment entry point; the platform controls PORT."""
import os
import uvicorn

if __name__ == '__main__':
    uvicorn.run('backend.app:app', host='0.0.0.0', port=int(os.getenv('PORT', '8787')),
                workers=1, limit_concurrency=24, timeout_keep_alive=5,
                timeout_graceful_shutdown=55, proxy_headers=False)
