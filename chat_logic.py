import google.generativeai as genai
import os
from dotenv import load_dotenv
import logging
from google.generativeai.types import GenerationConfig, ContentDict, PartDict
from google.ai.generativelanguage import SafetySetting, HarmCategory
import io

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()
API_KEY = os.getenv("GOOGLE_API_KEY")

if not API_KEY:
    logger.error("GOOGLE_API_KEY not found in environment variables.")

try:
    genai.configure(api_key=API_KEY)
except Exception as e:
    logger.error(f"Failed to configure Google Generative AI: {e}")

MODEL_NAME = "gemini-2.5-flash-preview-05-20"

# System Prompt (Bengali Chemistry Expert with Image Capability)
SYSTEM_PROMPT = """
**Your Role:**
You are an expert Chemistry teacher ("রসায়ন বিশেষজ্ঞ") for Class 11 and 12 students (Indian syllabus: WBCHSE, CBSE, ISC). Your main job is to help them understand and solve Chemistry problems by providing direct, clear answers in Bengali. You can now understand questions from images.

**Language:**
You MUST reply ONLY in simple, everyday Kolkata Bengali (সহজ কথ্য কলকাতা বাংলা). All explanations and examples must be in this language.

**How to Answer (Core Instructions):**
1.  **Get the Input:** A student will ask a chemistry question. This might be text-only, an image of a question (e.g., from a textbook, a diagram, or a chemical structure), or a mix of text and an image.
2.  **Understand and Analyze:**
    * Carefully look at any images. Identify text, diagrams, chemical structures, or specific elements in the image that are part of the question.
    * Read any accompanying text.
    * Use your "thinking" to understand the core chemistry concept.
    * Break down the problem step-by-step in your mind.
3.  **Give Only the Answer (শুধু উত্তর দিন):**
    * Provide *only the direct answer* in Bengali. No extra talk, no greetings (like "নমস্কার" or "হ্যালো"), no goodbyes.
    * Explain the chemistry principles clearly.
    * If it's a problem to solve (e.g., balancing equations, stoichiometry, organic mechanisms), show the steps in Bengali.
    * Use very simple Bengali that Class 11/12 students can easily understand.
    * Be detailed and complete.
    * Use examples if they help.
    * Format your answers for easy reading: use bullet points, make important Bengali terms **bold**, and use line breaks.
4.  **Handling "Regenerate" or "Simplify" (পুনরায় বলুন / আরও সোজা করুন):**
    * If the student asks to **"আবার বলুন" (Say again/Regenerate)** or something similar about the last answer, give a *different explanation or solution* in Bengali for the *same original question* (including any image context). Try a new angle or different examples, keeping it detailed and correct. Assume they are referring to the last question you answered.
    * If the student asks to **"আরও সোজা করে বলুন" (Explain more simply/Simplify)** or something similar about the last answer, make your *previous Bengali explanation/solution simpler*. Break it into easier steps or use more basic Bengali words. Don't leave out important info, just make it clearer. Assume they are referring to the last answer you provided.
5.  **If an Image is Unclear (ছবি পরিষ্কার না হলে):**
    * If an uploaded image is blurry, unreadable, or doesn't seem to contain a clear chemistry question, politely ask the student (in Bengali) to upload a clearer image or type the question. For example: "ছবিটা ঠিকঠাক বোঝা যাচ্ছে না। আর একটু পরিষ্কার ছবি দেবেন বা প্রশ্নটা লিখে জানাবেন?" (The image isn't clear. Could you provide a clearer picture or type out the question?)

**Your Tone (আপনার বলার ভঙ্গি):**
* **Helpful (সাহায্য করার মানসিকতা):** Help students learn.
* **Patient and Clear (ধৈর্য ধরে সহজ করে বোঝানো):** Explain tricky things calmly.
* **Accurate (সঠিক তথ্য):** Make sure your chemistry facts are right.
* **Focused (শুধুমাত্র পড়াশোনা):** Keep it focused on studies.

**What You Know (আপনার জ্ঞানের পরিধি):**
All Chemistry topics for Class 11 and 12 (WBCHSE, CBSE, ISC).
*(e.g., Physical Chemistry (ভৌত রসায়ন), Inorganic Chemistry (অজৈব রসায়ন), Organic Chemistry (জৈব রসায়ন) - cover all standard topics.)*

**Important Rules (জরুরী নিয়ম):**
* Only answer questions about Class 11/12 Chemistry.
* Don't chat about other things.
* If a question (text or image) isn't clear, ask for more details in simple Bengali. Example: "প্রশ্নটা আর একটু বুঝিয়ে বললে ভালো হয়।" (It would be better if you explained the question a bit more.)
* **CRITICAL (সবচেয়ে গুরুত্বপূর্ণ): Provide ONLY the answer in Bengali. Do NOT add any extra text before or after the main answer. No introductions, no greetings, no summaries, no "hope this helps," no "I am an AI," and absolutely no disclaimers. Just the answer itself, directly addressing the question in Bengali.**
"""

generation_config = GenerationConfig(
    temperature=0.6,
    top_p=0.95,
    top_k=64,
    max_output_tokens=65536,
    response_mime_type="text/plain",
)

safety_settings = [
    SafetySetting(category=HarmCategory.HARM_CATEGORY_HARASSMENT, threshold=SafetySetting.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE),
    SafetySetting(category=HarmCategory.HARM_CATEGORY_HATE_SPEECH, threshold=SafetySetting.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE),
    SafetySetting(category=HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT, threshold=SafetySetting.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE),
    SafetySetting(category=HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT, threshold=SafetySetting.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE),
]

active_bengali_chem_chats = {}
last_bengali_chem_questions_context = {}
last_bengali_chem_answers = {}

def start_bengali_chem_chat(session_id: str):
    logger.info(f"Starting new Bengali Chemistry chat session: {session_id}")
    try:
        model = genai.GenerativeModel(
            model_name=MODEL_NAME,
            safety_settings=safety_settings,
            generation_config=generation_config,
            system_instruction=SYSTEM_PROMPT,
        )
        chat_session = model.start_chat(history=[])
        active_bengali_chem_chats[session_id] = chat_session
        last_bengali_chem_questions_context[session_id] = {'text': None, 'image_parts': None}
        last_bengali_chem_answers[session_id] = None
        return chat_session
    except Exception as e:
        logger.error(f"Error initializing model for Bengali Chemistry chat session {session_id}: {e}")
        raise

def send_bengali_chem_message(session_id: str, text_message: str | None = None, image_data: bytes | None = None, image_mime_type: str | None = None, action: str = "ask"):
    if session_id not in active_bengali_chem_chats:
        logger.warning(f"Bengali Chemistry session ID {session_id} not found. Starting new chat.")
        start_bengali_chem_chat(session_id)

    chat_session = active_bengali_chem_chats[session_id]
    
    content_parts = []
    current_question_text_for_logging = text_message
    current_image_parts_for_context = None

    if image_data and image_mime_type:
        current_image_parts_for_context = [PartDict(inline_data=PartDict(data=image_data, mime_type=image_mime_type))]

    if action == "ask":
        if text_message:
            content_parts.append(PartDict(text=text_message))
        if current_image_parts_for_context:
            content_parts.extend(current_image_parts_for_context)
        last_bengali_chem_questions_context[session_id] = {'text': text_message, 'image_parts': current_image_parts_for_context}

    elif action == "regenerate":
        prev_context = last_bengali_chem_questions_context.get(session_id, {})
        original_text = prev_context.get('text')
        original_image_parts = prev_context.get('image_parts')
        
        # The system prompt handles "আবার বলুন". This text is mainly for context if needed.
        prompt_text = "আগের উত্তরটা আবার বলুন।"
        if original_text:
            prompt_text += f" (আগের প্রশ্ন ছিল: '{original_text[:50]}...')"
        
        content_parts.append(PartDict(text=prompt_text))
        if original_image_parts:
            content_parts.extend(original_image_parts)
        current_question_text_for_logging = prompt_text

    elif action == "simplify":
        prev_answer = last_bengali_chem_answers.get(session_id)
        # The system prompt handles "আরও সোজা করে বলুন".
        prompt_text = "আগের উত্তরটা আরও সোজা করে বলুন।"
        if prev_answer:
            prompt_text += f" (আগের উত্তর ছিল: \"{prev_answer[:70]}...\")"
            
        content_parts.append(PartDict(text=prompt_text))
        current_question_text_for_logging = prompt_text
    
    if not content_parts:
        logger.warning(f"No content to send for Bengali Chemistry session {session_id} with action {action}.")
        return "দুঃখিত, আপনার প্রশ্নটি বুঝতে পারিনি বা আগের কোনো আলোচনার সূত্র খুঁজে পাচ্ছি না।" # Sorry, I couldn't understand your question or find context from previous discussion.

    logger.info(f"Sending to Bengali Chem session {session_id} (action: {action}): Text='{current_question_text_for_logging[:70] if current_question_text_for_logging else 'N/A'}' Image parts present: {bool(current_image_parts_for_context or (action == 'regenerate' and last_bengali_chem_questions_context.get(session_id, {}).get('image_parts')))}")

    try:
        response = chat_session.send_message(content_parts)
        
        if not response.parts:
            block_reason = response.prompt_feedback.block_reason.name if response.prompt_feedback and response.prompt_feedback.block_reason else "UNKNOWN_REASON"
            logger.warning(f"Response potentially blocked for Bengali Chem session {session_id}. Reason: {block_reason}")
            return f"আমার উত্তর দেওয়া সম্ভব হচ্ছে না ({block_reason})। অনুগ্রহ করে আপনার প্রশ্নটি অন্যভাবে করার চেষ্টা করুন।" # My response isn't possible due to X. Please try to ask your question differently.

        response_text = "".join(part.text for part in response.parts if hasattr(part, 'text'))
        last_bengali_chem_answers[session_id] = response_text

        logger.debug(f"Bengali Chem session {session_id} history length: {len(chat_session.history)}")
        return response_text

    except Exception as e:
        logger.error(f"Error during send_message for Bengali Chem session {session_id}: {e}", exc_info=True)
        return f"দুঃখিত, আপনার অনুরোধটি প্রক্রিয়া করার সময় একটি ত্রুটি ঘটেছে: {e}" 