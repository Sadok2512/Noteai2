from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app import auth, transcribe, auth_verify

app = FastAPI(title="NoteAI Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/auth")
app.include_router(transcribe.router)
app.include_router(auth_verify.router)

@app.get("/")
def root():
    return {"message": "NoteAI backend is running."}
