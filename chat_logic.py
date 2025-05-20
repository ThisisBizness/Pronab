import google.generativeai as genai
import os
from dotenv import load_dotenv
import logging
from google.generativeai.types import GenerationConfig
from google.ai.generativelanguage import SafetySetting, HarmCategory

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()
API_KEY = os.getenv("GOOGLE_API_KEY")

if not API_KEY:
    logger.error("GOOGLE_API_KEY not found in environment variables.")
    # Consider raising an error or handling this more gracefully in a production app
    # For now, we'll let it proceed, but genai.configure will likely fail.

try:
    genai.configure(api_key=API_KEY)
except Exception as e:
    logger.error(f"Failed to configure Google Generative AI: {e}")
    # Handle configuration error

# --- Model Configuration ---
MODEL_NAME = "gemini-2.5-flash-preview-04-17" # Updated to gemini-1.5-flash-latest

# System Prompt defining the chatbot's persona and behavior
SYSTEM_PROMPT = """
**Your Role:**
You are a Chemistry expert for Class 11 and 12 students (Indian syllabus like WBCHSE, CBSE, ISC). Your main job is to help them understand and solve Chemistry problems by providing direct, clear answers.

**Language:**
You MUST reply ONLY in simple, everyday Kolkata Bengali (সহজ কথ্য কলকাতা বাংলা). All explanations and examples should be in this language.

**How to Answer (Core Instructions):**
1.  **Get the Question:** A student will ask a chemistry question.
2.  **Think and Understand:** Carefully understand the question. Break it down step-by-step in your mind to figure out the main concepts and how to answer fully and correctly.
3.  **Give Only the Answer:**
    * Provide *only the direct answer* to the question. No extra talk, no greetings, no goodbyes.
    * Explain the chemistry concepts behind the question.
    * If it's a math-type problem, show the steps to solve it.
    * Use very simple Bengali that Class 11/12 students can easily understand.
    * Be detailed and complete in your answer.
    * Use examples if they help explain.
    * Make your answers easy to read. Use bullet points, make important Bengali words bold, and use line breaks.

4.  **Handling "Regenerate" or "Simplify":**
    * If the student asks to **"আবার বলো" (Say again/Regenerate)** or something similar about the last answer, give a *different explanation or solution* for the *same original question*. Try a new angle or different examples, but keep the answer detailed and correct. Assume they are referring to the last question you answered.
    * If the student asks to **"আরও সোজা করে বলো" (Explain more simply/Simplify)** or something similar about the last answer, make your *previous explanation/solution simpler*. Break it into easier steps or use more basic words. Don't leave out important info, just make it clearer. Assume they are referring to the last answer you provided.

**Your Tone:**
* **Helpful (সাহায্য করার মানসিকতা):** Help students learn.
* **Patient and Clear (ধৈর্য ধরে সহজ করে বোঝানো):** Explain tricky things calmly.
* **Correct (সঠিক তথ্য):** Make sure your chemistry facts are right.
* **Serious (গুরুত্বপূর্ণ):** Keep it focused on studies.

**What You Know (Scope):**
All Chemistry topics for Class 11 and 12, including:
* Physical Chemistry (ভৌত রসায়ন): e.g., Atomic Structure (পরমাণুর গঠন), Chemical Bonding (রাসায়নিক বন্ধন), Thermodynamics (তাপগতিবিদ্যা), Solutions (দ্রবণ), Electrochemistry (তড়িৎরসায়ন), Chemical Kinetics (রাসায়নিক গতিবিদ্যা).
* Inorganic Chemistry (অজৈব রসায়ন): e.g., p-block elements (পি-ব্লক মৌল), d-block elements (ডি-ব্লক মৌল), Coordination Compounds (জটিল যৌগ).
* Organic Chemistry (জৈব রসায়ন): e.g., Hydrocarbons (হাইড্রোকার্বন), Alcohols (অ্যালকোহল), Aldehydes (অ্যালডিহাইড), Biomolecules (জৈব অণু).
    *(This is just a sample, cover all standard topics for these classes.)*

**Important Rules (Limitations):**
* Only answer questions about Class 11/12 Chemistry.
* Don't chat about other things.
* If a question isn't clear or is missing info, ask the student to explain more (in simple Kolkata Bengali). For example, say: "প্রশ্নটা ঠিক বুঝতে পারলাম না, আর একটু খুলে বলবে?" (Didn't quite get the question, can you explain a bit more?) or "এইটা উত্তর দেওয়ার জন্য আরও কিছু তথ্য লাগবে।" (Need a bit more info to answer this.)
* **CRITICAL: Do NOT add any extra text before or after the main answer. No introductions, no greetings, no summaries, no "hope this helps," no "I am an AI," and absolutely no disclaimers. Just the answer itself, directly addressing the question.**
"""

# Generation Configuration
generation_config = GenerationConfig(
    temperature=0.6, # Slightly lower for more factual/consistent chemistry answers
    top_p=0.95,
    top_k=64,
    max_output_tokens=65536, # Increased for potentially detailed chemistry answers
    response_mime_type="text/plain",
)

# Safety Settings - Adjust as needed
safety_settings = [
    SafetySetting(
        category=HarmCategory.HARM_CATEGORY_HARASSMENT,
        threshold=SafetySetting.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE
    ),
    SafetySetting(
        category=HarmCategory.HARM_CATEGORY_HATE_SPEECH,
        threshold=SafetySetting.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE
    ),
    SafetySetting(
        category=HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
        threshold=SafetySetting.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE
    ),
    SafetySetting(
        category=HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
        threshold=SafetySetting.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE
    ),
]

# --- Chat Session Management ---
# Store active chat sessions in memory
active_chats = {} # Key: session_id (string), Value: genai.ChatSession object
last_questions = {} # Key: session_id, Value: last_user_question
last_answers = {} # Key: session_id, Value: last_bot_answer

def start_new_chat(session_id: str):
    """Starts a new chat session with the specified configuration."""
    logger.info(f"Starting new chat session: {session_id}")
    try:
        model = genai.GenerativeModel(
            model_name=MODEL_NAME,
            safety_settings=safety_settings,
            generation_config=generation_config,
            system_instruction=SYSTEM_PROMPT,
        )
        # Initialize with an empty history, or a pre-defined first message if desired.
        # For "thinking on", the model itself is designed for reasoning.
        # We encourage step-by-step thinking in the system prompt.
        chat_session = model.start_chat(history=[])
        active_chats[session_id] = chat_session
        last_questions[session_id] = None # Initialize last question
        last_answers[session_id] = None # Initialize last answer
        return chat_session
    except Exception as e:
        logger.error(f"Error initializing model or starting chat for session {session_id}: {e}")
        raise

def send_message_to_model(session_id: str, message: str, is_follow_up: str = None):
    """
    Sends a message to the chat session and returns the response.
    is_follow_up can be "regenerate" or "simplify".
    """
    if session_id not in active_chats:
        logger.warning(f"Session ID {session_id} not found. Starting new chat.")
        start_new_chat(session_id)

    chat_session = active_chats[session_id]
    
    # Construct the message for the model
    current_message_for_model = message

    if is_follow_up == "regenerate":
        original_question = last_questions.get(session_id)
        if original_question:
            # We don't send "regenerate" directly. The system prompt handles the phrasing.
            # We resend the original question implicitly by how the user will phrase it in Bengali.
            # Or, we can guide the model more explicitly if needed.
            # For this setup, we'll rely on the user clicking a "Regenerate" button
            # which sends a message like "আগের উত্তরটা আবার তৈরি করুন" (Regenerate the previous answer)
            # The system prompt is designed to understand this context.
            current_message_for_model = f"পূর্ববর্তী প্রশ্নের ({original_question}) উত্তরটি পুনরায় তৈরি করুন।"
            logger.info(f"Regenerating answer for original question: {original_question}")
        else:
            # Fallback if there's no last question stored for regeneration
            current_message_for_model = message # Or handle as an error/clarification
            logger.warning(f"Regenerate called for session {session_id} but no previous question found.")


    elif is_follow_up == "simplify":
        previous_answer = last_answers.get(session_id)
        if previous_answer:
            # Similar to regenerate, the user's click on "Simplify" will send a specific Bengali phrase.
            # The system prompt is designed to handle "আরও সহজ করুন"
            # We can make it more robust by passing the previous answer if the model struggles with context.
            current_message_for_model = f"আমার আগের প্রশ্নের উত্তরটি ({previous_answer}) আরও সহজ করে বুঝিয়ে দিন।"
            logger.info(f"Simplifying previous answer for session {session_id}")
        else:
            # Fallback if there's no last answer stored for simplification
            current_message_for_model = message # Or handle as an error/clarification
            logger.warning(f"Simplify called for session {session_id} but no previous answer found.")
    else:
        # This is a new question
        last_questions[session_id] = message


    logger.info(f"Sending message to session {session_id}: '{current_message_for_model[:100]}...'")

    try:
        response = chat_session.send_message(current_message_for_model)
        logger.info(f"Received response for session {session_id}")

        if not response.parts:
            logger.warning(f"Response potentially blocked for session {session_id}. Finish reason: {response.prompt_feedback.block_reason if response.prompt_feedback else 'N/A'}")
            block_reason_text = response.prompt_feedback.block_reason.name if response.prompt_feedback and response.prompt_feedback.block_reason else "UNKNOWN_REASON"
            # Bengali error message
            return f"দুঃখিত, আমি এই মুহূর্তে উত্তর দিতে পারছি না ({block_reason_text})। আপনি কি অন্যভাবে জিজ্ঞাসা করতে পারেন?"

        response_text = "".join(part.text for part in response.parts)

        # Store the latest answer only if it's not a follow-up that modifies a previous one in place
        if not is_follow_up: # Or based on specific logic for your app
            last_answers[session_id] = response_text

        logger.debug(f"Session {session_id} history length: {len(chat_session.history)}")
        return response_text

    except Exception as e:
        logger.error(f"Error during send_message for session {session_id}: {e}")
        # Bengali error message
        return f"দুঃখিত, আপনার অনুরোধটি প্রক্রিয়া করার সময় একটি ত্রুটি ঘটেছে: {e}" 