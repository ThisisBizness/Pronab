from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
import logging
import uuid # To generate unique session IDs
import os

# Import the chat logic functions
from chat_logic import send_message_to_model, start_new_chat, active_chats, logger, last_questions, last_answers

# Define the request body structure
class QuestionRequest(BaseModel):
    session_id: str | None = None
    question: str
    action: str | None = None # "ask", "regenerate", "simplify"

# Define the response body structure
class AnswerResponse(BaseModel):
    session_id: str
    answer: str
    # language: str # If you want to confirm language, though it's set in prompt

# Initialize FastAPI app
app = FastAPI(
    title="রসায়ন সহায়িকা (Chemistry Assistant)",
    description="দ্বাদশ ও একাদশ শ্রেণীর রসায়ন প্রশ্নোত্তর",
    version="0.1.0"
)

# Mount static files
static_dir = os.path.join(os.path.dirname(__file__), "static")
if not os.path.exists(static_dir):
    os.makedirs(static_dir) # Create if it doesn't exist
    logger.info(f"Created static directory at {static_dir}")

try:
    app.mount("/static", StaticFiles(directory=static_dir), name="static")
    logger.info(f"Mounted static directory from {static_dir}")
except RuntimeError as e:
    logger.warning(f"Could not mount static directory: {e}. Ensure 'static' directory exists at {static_dir}.")


# --- API Endpoints ---

@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def read_root(request: Request):
    """Serves the HTML interface."""
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


@app.post("/ask", response_model=AnswerResponse)
async def ask_question_endpoint(req_body: QuestionRequest):
    """
    Receives a chemistry question, interacts with the Gemini model,
    and returns the answer. Handles new questions, regeneration, and simplification.
    """
    session_id = req_body.session_id
    user_message = req_body.question # This will be the question or a command like "simplify"
    action = req_body.action if req_body.action else "ask" # Default to "ask"

    if not user_message and action == "ask": # Only require message if it's a new question
        raise HTTPException(status_code=400, detail="প্রশ্ন خالی হতে পারে না (Question cannot be empty).")

    # If no session_id is provided for a new question, start a new chat
    if not session_id:
        if action != "ask":
             raise HTTPException(status_code=400, detail="পুনরায় তৈরি বা সহজ করার জন্য একটি সক্রিয় সেশন প্রয়োজন (Session ID is required for regenerate/simplify).")
        session_id = str(uuid.uuid4())
        try:
            start_new_chat(session_id)
            logger.info(f"Started new session: {session_id}")
        except Exception as e:
            logger.error(f"Failed to start new chat session {session_id}: {e}")
            raise HTTPException(status_code=500, detail=f"Could not initialize chat session: {e}")
    elif session_id not in active_chats:
        # If session_id is provided but not found (e.g. server restart, or invalid ID from client)
        logger.warning(f"Session ID {session_id} provided but not found. Starting new chat for this ID.")
        try:
            start_new_chat(session_id) # Re-initialize if not found
        except Exception as e:
            logger.error(f"Failed to re-initialize chat session {session_id}: {e}")
            raise HTTPException(status_code=500, detail=f"Could not initialize chat session: {e}")

    # Prepare message for the model based on action
    message_for_model = user_message
    is_follow_up_action = None

    if action == "regenerate":
        is_follow_up_action = "regenerate"
        # The user_message for "regenerate" could be a placeholder like "regenerate_previous"
        # or the system prompt handles generic "regenerate" requests based on Bengali phrasing.
        # `send_message_to_model` will use `last_questions[session_id]`
        message_for_model = "পূর্ববর্তী উত্তরটি আবার তৈরি করুন।" # Standard Bengali phrase
        if not last_questions.get(session_id):
            raise HTTPException(status_code=404, detail="পুনরায় তৈরি করার জন্য কোনও পূর্ববর্তী প্রশ্ন পাওয়া যায়নি। (No previous question found to regenerate.)")
    elif action == "simplify":
        is_follow_up_action = "simplify"
        message_for_model = "পূর্ববর্তী উত্তরটি আরও সহজ করুন।" # Standard Bengali phrase
        if not last_answers.get(session_id):
            raise HTTPException(status_code=404, detail="সহজ করার জন্য কোনও পূর্ববর্তী উত্তর পাওয়া যায়নি। (No previous answer found to simplify.)")
    # If action is "ask", message_for_model is already user_message (the question)

    try:
        bot_response = send_message_to_model(session_id, message_for_model, is_follow_up=is_follow_up_action)
        return AnswerResponse(session_id=session_id, answer=bot_response)

    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Unhandled exception in /ask endpoint for session {session_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"একটি অভ্যন্তরীণ সার্ভার ত্রুটি ঘটেছে: {e}")


@app.get("/health", status_code=200)
async def health_check():
    """Simple health check endpoint."""
    return {"status": "ok", "message": "রসায়ন সহায়িকা চলছে!"}

# --- Main execution block (for running locally with uvicorn) ---
if __name__ == "__main__":
    import uvicorn
    logger.info("Starting Uvicorn server locally for রসায়ন সহায়িকা...")
    if not os.getenv("GOOGLE_API_KEY"):
        logger.warning("GOOGLE_API_KEY not set in environment. Please create a .env file.")

    # Ensure the main:app string is correct if your file is named differently
    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        log_level="info"
    ) 