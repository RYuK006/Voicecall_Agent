import os
import uvicorn
from app.config import HOST, PORT

if __name__ == "__main__":
    is_termux = os.path.exists("/data/data/com.termux")
    bind_host = "0.0.0.0" if is_termux else HOST
    print(f"🚀 Starting Indic Voice Call Agent at http://{bind_host}:{PORT}")
    print(f"🎙️ Open your browser at http://localhost:{PORT} to test live calls.")
    uvicorn.run("app.server:app", host=bind_host, port=PORT, reload=not is_termux)
