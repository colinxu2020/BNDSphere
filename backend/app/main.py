from os import getenv

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(
    title = "BNDSphere API",
    description = "Backend Service for BNDSphere",
    version = "0.1.0",
    docs_url='/api/docs',
    openapi_url='/api/openapi.json'
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[getenv('BNDSPHERE_CORS_ORIGIN', '*')],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True
)
if getenv("BNDSPHERE_DEBUG", '0') == '1':
    app.debug = True
