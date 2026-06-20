import os
import uvicorn

if __name__ == "__main__":
    # Hugging Face Spaces sets PORT env var to 7860, default to 8000 for local dev
    port = int(os.getenv("PORT", 8000))
    # Disable reload in production to conserve memory and improve performance
    reload = os.getenv("ENV", "development").lower() == "development"
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=reload)
