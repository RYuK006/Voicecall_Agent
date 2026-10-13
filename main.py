import uvicorn
from app.config import HOST, PORT

if __name__ == "__main__":
    print(f"🚀 Starting Indic Voice Call Agent at http://{HOST}:{PORT}")
    print(f"🎙️ Open your browser at http://localhost:{PORT} to test live calls.")
    uvicorn.run("app.server:app", host=HOST, port=PORT, reload=True)
