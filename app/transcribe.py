from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from pydantic import BaseModel
from pymongo import MongoClient
from bson import ObjectId
from pydub.utils import mediainfo
import datetime, requests, os, gridfs, traceback

router = APIRouter()

REPLICATE_API_TOKEN = os.getenv("REPLICATE_API_TOKEN")
client = MongoClient(os.getenv("MONGODB_URI"))
db = client["noteai"]
fs = gridfs.GridFS(db)
notes_collection = db["notes"]

class NoteMetadataResponse(BaseModel):
    id: str
    user_id: str
    filename: str
    uploaded_at: str
    content_type: str
    transcription: str = ""
    summary: str = ""
    tasks: list = []
    size_bytes: int = 0
    custom_name: str = None
    comment: str = None
    source: str = "WEB"
    duration_sec: float = 0.0

def get_audio_duration_seconds(path: str) -> float:
    try:
        return float(mediainfo(path)["duration"])
    except:
        return 0.0

def upload_temp_file_to_fileio(path: str) -> str:
    try:
        with open(path, "rb") as f:
            res = requests.post("https://file.io", files={"file": f})
        return res.json().get("link")
    except:
        return None

@router.post("/transcribe-replicate", response_model=NoteMetadataResponse)
async def transcribe_replicate(
    file: UploadFile = File(...),
    user_id: str = Form(...),
    custom_name: str = Form(""),
    comment: str = Form("")
):
    try:
        if not REPLICATE_API_TOKEN:
            raise HTTPException(status_code=500, detail="Token Replicate manquant.")
        content = await file.read()
        file_id = fs.put(content, filename=file.filename, content_type=file.content_type)
        file_id_str = str(file_id)
        temp_path = f"/tmp/{file_id_str}.webm"
        with open(temp_path, "wb") as f:
            f.write(content)
        duration_sec = get_audio_duration_seconds(temp_path)
        audio_url = upload_temp_file_to_fileio(temp_path)
        if not audio_url:
            raise HTTPException(status_code=500, detail="Échec de l'upload vers file.io")
        headers = {
            "Authorization": f"Token {REPLICATE_API_TOKEN}",
            "Content-Type": "application/json"
        }
        response = requests.post(
            "https://api.replicate.com/v1/predictions",
            headers=headers,
            json={"version": "a8f5d465f5f5ad6c50413e4f5c3f73292f7e43e2c7e15c76502a89cbd8b6ec1e",
                  "input": {"audio": audio_url}},
            timeout=90
        )
        response.raise_for_status()
        transcription = response.json().get("output", "[Transcription non disponible]")
        os.remove(temp_path)
        metadata = {
            "_id": file_id_str,
            "user_id": user_id,
            "filename": file.filename,
            "custom_name": custom_name,
            "comment": comment,
            "uploaded_at": datetime.datetime.utcnow().isoformat(),
            "content_type": file.content_type,
            "size_bytes": len(content),
            "duration_sec": duration_sec,
            "transcription": transcription,
            "summary": "À traiter",
            "tasks": [],
            "source": "WEB"
        }
        notes_collection.insert_one(metadata)
        return NoteMetadataResponse(id=file_id_str, **metadata)
    except Exception as e:
        tb = traceback.format_exc()
        print("Erreur:", tb)
        raise HTTPException(status_code=500, detail="Erreur interne serveur.")