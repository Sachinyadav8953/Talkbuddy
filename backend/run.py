import os
import uvicorn

if __name__ == "__main__":
    # Render sets PORT env var (usually 10000), Hugging Face sets 7860, default to 8000 for local dev
    port = int(os.getenv("PORT", 8000))
    
    # Check if running in a cloud/production environment
    is_render = bool(os.getenv("RENDER") or os.getenv("RENDER_SERVICE_ID"))
    is_cloud = is_render or bool(os.getenv("SPACE_ID") or os.getenv("RAILWAY_ENVIRONMENT") or os.getenv("PORT"))
    
    # Reload MUST be False in production/Render. File downloads in models/ and piper_bin
    # cause watchfiles to trigger reload loops and prevent port binding.
    env = os.getenv("ENV", "production" if is_cloud else "development").lower()
    reload = (env == "development") and not is_cloud

    print(f"Starting TalkBuddy backend on 0.0.0.0:{port} (reload={reload}, env={env})")
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=reload)