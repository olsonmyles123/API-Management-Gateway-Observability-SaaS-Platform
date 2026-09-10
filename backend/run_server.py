import uvicorn
import os
import sys

# Ensure backend root is on Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.config import settings

if __name__ == "__main__":
    print(f"================================================================")
    print(f"🚀 Starting {settings.PROJECT_NAME} v{settings.VERSION}")
    print(f"🌐 Data Plane & Control Plane listening on http://{settings.HOST}:{settings.PORT}")
    print(f"📚 OpenAPI Documentation available at http://localhost:{settings.PORT}/docs")
    print(f"================================================================")
    
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=(settings.ENVIRONMENT == "development"),
        log_level=settings.LOG_LEVEL.lower(),
    )
