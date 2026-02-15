"""
Main FastAPI application for Fraud Ring Detection System
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import logging

# Import routes
from routes.graph import router as graph_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Fraud Ring Detection API",
    description="Advanced graph-based fraud detection for Medicaid provider networks",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(graph_router)

@app.get("/", response_class=HTMLResponse)
async def root():
    """Root endpoint with API information"""
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Fraud Ring Detection API</title>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
                padding: 20px;
            }
            .container {
                background: white;
                border-radius: 20px;
                padding: 48px;
                max-width: 800px;
                box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
            }
            h1 {
                font-size: 36px;
                color: #1a202c;
                margin-bottom: 16px;
                display: flex;
                align-items: center;
                gap: 12px;
            }
            .subtitle {
                font-size: 18px;
                color: #718096;
                margin-bottom: 32px;
            }
            .endpoints {
                background: #f8f9fa;
                border-radius: 12px;
                padding: 24px;
                margin-bottom: 24px;
            }
            .endpoint {
                padding: 12px;
                margin: 8px 0;
                background: white;
                border-radius: 8px;
                border-left: 4px solid #667eea;
            }
            .endpoint-method {
                display: inline-block;
                background: #667eea;
                color: white;
                padding: 4px 12px;
                border-radius: 6px;
                font-size: 12px;
                font-weight: 600;
                margin-right: 12px;
            }
            .endpoint-path {
                font-family: 'Courier New', monospace;
                color: #2d3748;
                font-weight: 600;
            }
            .endpoint-desc {
                color: #718096;
                font-size: 14px;
                margin-top: 8px;
            }
            .links {
                display: flex;
                gap: 16px;
                margin-top: 32px;
            }
            .btn {
                flex: 1;
                padding: 14px 24px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                text-decoration: none;
                border-radius: 10px;
                text-align: center;
                font-weight: 600;
                transition: transform 0.2s ease;
                box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
            }
            .btn:hover {
                transform: translateY(-2px);
                box-shadow: 0 8px 20px rgba(102, 126, 234, 0.4);
            }
            .status {
                display: inline-block;
                padding: 8px 16px;
                background: #D4EDDA;
                color: #155724;
                border-radius: 20px;
                font-size: 14px;
                font-weight: 600;
                margin-bottom: 24px;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🕸️ Fraud Ring Detection API</h1>
            <p class="subtitle">Advanced graph-based fraud detection for provider networks</p>
            
            <div class="status">🟢 API Status: Online</div>
            
            <div class="endpoints">
                <h2 style="margin-bottom: 16px; color: #2d3748;">Available Endpoints</h2>
                
                <div class="endpoint">
                    <span class="endpoint-method">GET</span>
                    <span class="endpoint-path">/api/graph/network/{provider_id}</span>
                    <div class="endpoint-desc">Get ego network for a specific provider</div>
                </div>
                
                <div class="endpoint">
                    <span class="endpoint-method">GET</span>
                    <span class="endpoint-path">/api/graph/fraud-rings</span>
                    <div class="endpoint-desc">Detect fraud rings using community detection</div>
                </div>
                
                <div class="endpoint">
                    <span class="endpoint-method">GET</span>
                    <span class="endpoint-path">/api/graph/kickback-cycles</span>
                    <div class="endpoint-desc">Identify circular referral patterns</div>
                </div>
                
                <div class="endpoint">
                    <span class="endpoint-method">GET</span>
                    <span class="endpoint-path">/api/graph/beneficiary-concentration</span>
                    <div class="endpoint-desc">Find providers sharing beneficiaries</div>
                </div>
                
                <div class="endpoint">
                    <span class="endpoint-method">GET</span>
                    <span class="endpoint-path">/api/graph/network-stats</span>
                    <div class="endpoint-desc">Get comprehensive network analysis</div>
                </div>
                
                <div class="endpoint">
                    <span class="endpoint-method">GET</span>
                    <span class="endpoint-path">/api/graph/health</span>
                    <div class="endpoint-desc">Check API health status</div>
                </div>
            </div>
            
            <div class="links">
                <a href="/api/docs" class="btn">📚 Interactive API Docs</a>
                <a href="/api/redoc" class="btn">📖 API Reference</a>
            </div>
        </div>
    </body>
    </html>
    """

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "Fraud Ring Detection API",
        "version": "1.0.0"
    }

if __name__ == "__main__":
    import uvicorn
    logger.info("Starting Fraud Ring Detection API...")
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
