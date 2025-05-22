from fastapi import FastAPI, HTTPException, Request, File, UploadFile, Form
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
import logging
import uuid
import os

# Renaming imported functions to avoid conflicts if you were to merge apps later
from chat_logic import (
    send_bengali_chem_message,
    start_bengali_chem_chat,
    active_bengali_chem_chats, # Ensure these dicts are unique per app logic
    last_bengali_chem_questions_context,
    last_bengali_chem_answers,
    logger # Use the same logger or a specific one
)

# Initialize FastAPI app
app = FastAPI(
    title="রসায়ন সহায়িকা (Chemistry Helper - Class 11/12)",
    description="রসায়নের প্রশ্ন করুন (ছবিসহ) - Pronab Sarkar (Ph: 8906663446, 6296024737)",
    version="1.1.0" # Version update
)

# Mount static files
static_dir = os.path.join(os.path.dirname(__file__), "static")
if not os.path.exists(static_dir):
    os.makedirs(static_dir)
    logger.info(f"Created static directory at {static_dir}")

try:
    app.mount("/static", StaticFiles(directory=static_dir), name="static")
    logger.info(f"Mounted static directory from {static_dir}")
except RuntimeError as e:
    logger.warning(f"Could not mount static directory: {e}. Ensure 'static' directory exists at {static_dir}.")


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def read_root(request: Request):
    index_html_path = os.path.join(static_dir, "index.html")
    try:
        with open(index_html_path, "r", encoding="utf-8") as f:
            html_content = f.read()
        return HTMLResponse(content=html_content)
    except FileNotFoundError:
        logger.error(f"{index_html_path} not found.")
        raise HTTPException(status_code=404, detail="Frontend interface not found.")
    except Exception as e:
        logger.error(f"Error reading {index_html_path}: {e}")
        raise HTTPException(status_code=500, detail="Server configuration error.")

class BengaliAnswerResponse(BaseModel):
    session_id: str
    answer: str # উত্তর

@app.post("/ask_bengali_chem", response_model=BengaliAnswerResponse) # New endpoint name
async def ask_bengali_chemistry_question(
    session_id: str | None = Form(None),
    question_text: str | None = Form(None), # প্রশ্ন (text)
    action: str = Form("ask"), # "ask", "regenerate", "simplify"
    image_file: UploadFile | None = File(None) # ছবি (image)
):
    current_session_id = session_id

    if action == "ask" and not question_text and not image_file:
        raise HTTPException(status_code=400, detail="অনুগ্রহ করে প্রশ্ন লিখুন অথবা ছবি আপলোড করুন।") # Please write a question or upload an image.

    if not current_session_id:
        if action != "ask":
            raise HTTPException(status_code=400, detail="অন্যান্য কাজের জন্য একটি সক্রিয় সেশন প্রয়োজন।") # A session is required for other actions.
        current_session_id = str(uuid.uuid4())
        try:
            start_bengali_chem_chat(current_session_id)
            logger.info(f"Started new Bengali Chemistry session: {current_session_id}")
        except Exception as e:
            logger.error(f"Failed to start new Bengali Chemistry session {current_session_id}: {e}")
            raise HTTPException(status_code=500, detail=f"সেশন শুরু করা যায়নি: {e}")
    elif current_session_id not in active_bengali_chem_chats:
        logger.warning(f"Bengali Chemistry session ID {current_session_id} provided but not found. Starting new chat.")
        try:
            start_bengali_chem_chat(current_session_id)
        except Exception as e:
            logger.error(f"Failed to re-initialize Bengali Chemistry session {current_session_id}: {e}")
            raise HTTPException(status_code=500, detail=f"সেশন পুনরায় শুরু করা যায়নি: {e}")

    image_data_bytes: bytes | None = None
    image_mime_type_str: str | None = None
    if image_file:
        allowed_mime_types = ["image/jpeg", "image/png", "image/webp", "image/gif", "image/heic", "image/heif"]
        if image_file.content_type not in allowed_mime_types:
            raise HTTPException(status_code=400, detail=f"এই ধরনের ছবি ({image_file.content_type}) সাপোর্ট করে না।") # This image type is not supported.
        
        image_data_bytes = await image_file.read()
        image_mime_type_str = image_file.content_type
        logger.info(f"Received image for Bengali Chem: {image_file.filename}, type: {image_mime_type_str}, size: {len(image_data_bytes)} bytes")

    message_for_logic = question_text
    # Logic for handling context for regenerate/simplify is within send_bengali_chem_message

    try:
        bot_response = send_bengali_chem_message(
            session_id=current_session_id,
            text_message=message_for_logic,
            image_data=image_data_bytes,
            image_mime_type=image_mime_type_str,
            action=action
        )
        return BengaliAnswerResponse(session_id=current_session_id, answer=bot_response)

    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Unhandled exception in /ask_bengali_chem for session {current_session_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"একটি অভ্যন্তরীণ সার্ভার ত্রুটি ঘটেছে: {e}")


@app.get("/health_bengali_chem", status_code=200) # New health check endpoint
async def health_check_bengali_chem():
    return {"status": "ok", "message": "রসায়ন সহায়িকা অ্যাপ চলছে!"} # Chemistry Helper App is running!

if __name__ == "__main__":
    import uvicorn
    logger.info("Starting Uvicorn server locally for Bengali Chemistry Helper...")
    if not os.getenv("GOOGLE_API_KEY"):
        logger.warning("GOOGLE_API_KEY not set in environment. Please create a .env file.")

    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        log_level="info"
    ) 