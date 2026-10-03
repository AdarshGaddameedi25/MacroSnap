"""
app.py
------
MacroSnap — AI Nutrition Buddy
Built with Streamlit + Google Gemini + Twilio WhatsApp.
Supports text chat, multimodal food photo analysis, nutrition summaries, and WhatsApp Sandbox notification.
"""

import streamlit as st
from google import genai
from google.genai import types
from twilio.rest import Client
from prompts import WELCOME_MESSAGE_TEMPLATE, SYSTEM_PROMPT, SUMMARY_REQUEST_PROMPT

# Supported image MIME types and extensions
ALLOWED_IMAGE_TYPES = {
    "image/jpeg": "jpeg",
    "image/jpg": "jpeg",
    "image/png": "png",
    "image/webp": "webp",
}
ALLOWED_EXTENSIONS = ("jpg", "jpeg", "png", "webp")


# ---------------------------------------------------------------------------
# Gemini Client — cached per Streamlit session
# ---------------------------------------------------------------------------
@st.cache_resource
def get_gemini_client():
    """Initialise and return a Google GenAI client using stored API key."""
    api_key = st.secrets.get("GEMINI_API_KEY", "")
    if not api_key or "PASTE_" in api_key:
        st.error(
            "⚠️ GEMINI_API_KEY is missing or unconfigured in .streamlit/secrets.toml. "
            "Please configure your API key and restart the app."
        )
        st.stop()
    return genai.Client(api_key=api_key)


# ---------------------------------------------------------------------------
# Twilio Client — cached per Streamlit session
# ---------------------------------------------------------------------------
@st.cache_resource
def get_twilio_client():
    """Initialise and return a Twilio Client using credentials in secrets.toml."""
    account_sid = st.secrets.get("TWILIO_ACCOUNT_SID", "")
    auth_token = st.secrets.get("TWILIO_AUTH_TOKEN", "")

    if not account_sid or not auth_token or "PASTE_" in account_sid or "PASTE_" in auth_token:
        st.error(
            "⚠️ Twilio credentials missing or unconfigured in .streamlit/secrets.toml. "
            "Please check TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN."
        )
        return None

    return Client(account_sid, auth_token)


def normalize_whatsapp_number(number: str) -> str:
    """
    Safely format any phone number into Twilio WhatsApp format (whatsapp:+...).
    Prevents duplicate country codes or double whatsapp: prefixes.
    """
    num = number.strip()
    if num.startswith("whatsapp:"):
        num = num.replace("whatsapp:", "").strip()
    if not num.startswith("+"):
        num = "+" + num
    return f"whatsapp:{num}"


def send_whatsapp_sandbox_message(to_number: str) -> tuple[bool, str, str]:
    """
    Send a WhatsApp message via Twilio Sandbox using the configured Content SID.
    Returns (success_boolean, status_message, info_disclaimer).
    """
    client = get_twilio_client()
    if client is None:
        return False, "Twilio client is unconfigured or missing valid credentials.", ""

    from_number = st.secrets.get("TWILIO_WHATSAPP_FROM", "")
    content_sid = st.secrets.get("TWILIO_CONTENT_SID", "")

    if not from_number or not content_sid or "PASTE_" in from_number or "PASTE_" in content_sid:
        return False, "Twilio WhatsApp sender or Content SID missing in secrets.toml.", ""

    normalized_to = normalize_whatsapp_number(to_number)

    try:
        message = client.messages.create(
            from_=from_number,
            to=normalized_to,
            content_sid=content_sid,
        )
        disclaimer = (
            "WhatsApp message sent using the Twilio Sandbox template. "
            "The current Sandbox template does not support the custom MacroSnap nutrition summary."
        )
        status = f"Message sent successfully to {normalized_to}! (Twilio SID: {message.sid})"
        return True, status, disclaimer
    except Exception as err:
        return False, f"Twilio API error: {str(err)}", ""


# ---------------------------------------------------------------------------
# Gemini Chat & Summary Helpers
# ---------------------------------------------------------------------------
def build_gemini_history(messages: list) -> list:
    """
    Convert MacroSnap session messages into the format expected by
    google-genai: a list of types.UserContent / types.ModelContent objects.
    Supports both text and image parts in multi-turn conversations.
    """
    history = []
    for i, msg in enumerate(messages):
        if i == 0 and msg["role"] == "assistant" and "Welcome to **MacroSnap**" in msg.get("content", ""):
            continue

        parts = []

        if msg.get("image_bytes") and msg.get("mime_type"):
            try:
                parts.append(
                    types.Part.from_bytes(
                        data=msg["image_bytes"],
                        mime_type=msg["mime_type"],
                    )
                )
            except Exception:
                pass

        if msg.get("content"):
            parts.append(types.Part(text=msg["content"]))

        if not parts:
            continue

        if msg["role"] == "user":
            history.append(types.UserContent(parts=parts))
        else:
            history.append(types.ModelContent(parts=parts))

    return history


def call_gemini(client, messages: list) -> str:
    """Send conversation history to Gemini and return the response."""
    history = build_gemini_history(messages)
    response = client.models.generate_content(
        model="gemini-3.8-flash",
        contents=history,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
        ),
    )
    return response.text


def generate_nutrition_summary(client, messages: list) -> str:
    """Send conversation history + SUMMARY_REQUEST_PROMPT to Gemini for a nutrition summary."""
    history = build_gemini_history(messages)
    summary_prompt_part = types.Part(text=SUMMARY_REQUEST_PROMPT)
    history.append(types.UserContent(parts=[summary_prompt_part]))

    response = client.models.generate_content(
        model="gemini-3.8-flash",
        contents=history,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
        ),
    )
    return response.text


# ---------------------------------------------------------------------------
# Page Configuration
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="MacroSnap",
    page_icon="🥗",
    layout="centered",
)


# ---------------------------------------------------------------------------
# Session State Initialization
# ---------------------------------------------------------------------------
def init_session_state():
    defaults = {
        "user_name": "",
        "whatsapp_number": "",
        "onboarding_completed": False,
        "messages": [],           # list of {"role": str, "content": str, "image_bytes": bytes|None, "mime_type": str|None}
        "uploader_key": 0,        # key to reset st.file_uploader after processing
        "nutrition_summary": "",  # generated nutrition summary text
        "wa_send_status": None,   # tuple of (is_success, status_msg, disclaimer_msg)
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


init_session_state()


# ---------------------------------------------------------------------------
# App Header — Always visible
# ---------------------------------------------------------------------------
st.title("🥗 MacroSnap")
st.caption(
    "Your AI nutrition buddy — describe a meal or upload a food photo "
    "and get estimated calories & macronutrients."
)
st.divider()


# ---------------------------------------------------------------------------
# ONBOARDING — shown only before the user has completed sign-in
# ---------------------------------------------------------------------------
if not st.session_state.onboarding_completed:

    st.subheader("👋 Let's get started")
    st.write("Tell us a little about yourself so we can personalise your experience.")

    with st.form(key="onboarding_form"):
        name_input = st.text_input(
            "Your name",
            placeholder="e.g. Adarsh",
            max_chars=50,
        )
        wa_input = st.text_input(
            "WhatsApp number (with country code)",
            placeholder="e.g. +919640953387",
            max_chars=20,
        )
        submitted = st.form_submit_button("Start MacroSnap 🚀", use_container_width=True)

    if submitted:
        name_clean = name_input.strip()
        wa_clean = wa_input.strip()

        errors = []
        if not name_clean:
            errors.append("Please enter your name.")
        if not wa_clean:
            errors.append("Please enter your WhatsApp number.")
        elif not wa_clean.startswith("+"):
            errors.append("WhatsApp number must start with a country code, e.g. +91…")

        if errors:
            for err in errors:
                st.error(err)
        else:
            st.session_state.user_name = name_clean
            st.session_state.whatsapp_number = wa_clean
            st.session_state.onboarding_completed = True

            welcome = WELCOME_MESSAGE_TEMPLATE.strip().replace(
                "**MacroSnap**", f"**MacroSnap**, {name_clean}"
            )
            st.session_state.messages.append(
                {"role": "assistant", "content": welcome, "image_bytes": None, "mime_type": None}
            )
            st.rerun()


# ---------------------------------------------------------------------------
# CHAT INTERFACE — shown after onboarding is complete
# ---------------------------------------------------------------------------
else:

    # --- Sidebar: user info + reset actions ---
    with st.sidebar:
        st.markdown(f"### 👤 {st.session_state.user_name}")
        st.markdown(f"📱 `{st.session_state.whatsapp_number}`")
        st.divider()

        # Summary action in sidebar
        if st.button("📋 Generate My Nutrition Summary", use_container_width=True, type="primary"):
            user_has_messages = any(msg["role"] == "user" for msg in st.session_state.messages)
            if not user_has_messages:
                st.warning("⚠️ No meal entries yet! Describe a meal or upload a food photo first.")
            else:
                client = get_gemini_client()
                with st.spinner("Generating your nutrition summary..."):
                    try:
                        summary_text = generate_nutrition_summary(client, st.session_state.messages)
                        st.session_state.nutrition_summary = summary_text
                        st.session_state.wa_send_status = None
                    except Exception as err:
                        st.error(f"⚠️ Failed to generate summary: {str(err)}")
                st.rerun()

        st.divider()

        if st.button("🗑️ Clear conversation", use_container_width=True):
            st.session_state.messages = []
            st.session_state.nutrition_summary = ""
            st.session_state.wa_send_status = None
            welcome = WELCOME_MESSAGE_TEMPLATE.strip().replace(
                "**MacroSnap**", f"**MacroSnap**, {st.session_state.user_name}"
            )
            st.session_state.messages.append(
                {"role": "assistant", "content": welcome, "image_bytes": None, "mime_type": None}
            )
            st.rerun()

        if st.button("🔄 Start over (new user)", use_container_width=True):
            for key in ["user_name", "whatsapp_number", "onboarding_completed", "messages", "uploader_key", "nutrition_summary", "wa_send_status"]:
                if key in st.session_state:
                    del st.session_state[key]
            st.rerun()

    # --- Display Summary Section if generated ---
    if st.session_state.get("nutrition_summary"):
        with st.container():
            st.markdown("### 📋 Your MacroSnap Summary")
            st.info(st.session_state.nutrition_summary)

            col1, col2 = st.columns([1, 1])
            with col1:
                if st.button("📱 Send to WhatsApp", use_container_width=True, type="primary"):
                    if not st.session_state.whatsapp_number:
                        st.error("⚠️ WhatsApp number missing. Please reset onboarding.")
                    else:
                        with st.spinner("Sending message via Twilio WhatsApp Sandbox..."):
                            success, status_msg, disclaimer = send_whatsapp_sandbox_message(
                                to_number=st.session_state.whatsapp_number
                            )
                            st.session_state.wa_send_status = (success, status_msg, disclaimer)
                        st.rerun()

            with col2:
                if st.button("🔄 Regenerate Summary", use_container_width=True):
                    client = get_gemini_client()
                    with st.spinner("Regenerating summary..."):
                        try:
                            summary_text = generate_nutrition_summary(client, st.session_state.messages)
                            st.session_state.nutrition_summary = summary_text
                            st.session_state.wa_send_status = None
                        except Exception as err:
                            st.error(f"⚠️ Failed to regenerate summary: {str(err)}")
                    st.rerun()

            # Display Twilio WhatsApp send status & template disclaimer if present
            if st.session_state.get("wa_send_status"):
                is_succ, status_msg, disclaimer_msg = st.session_state.wa_send_status
                if is_succ:
                    st.success(f"✅ {status_msg}")
                    if disclaimer_msg:
                        st.info(f"ℹ️ {disclaimer_msg}")
                else:
                    st.error(f"❌ {status_msg}")

            st.divider()

    # --- Render existing conversation history ---
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            if msg.get("image_bytes"):
                st.image(
                    msg["image_bytes"],
                    caption="Uploaded Food Photo 📸",
                    width=320,
                )
            if msg.get("content"):
                st.markdown(msg["content"])

    # --- Action Bar for Summary in Main View ---
    st.write("")
    gen_summary_btn = st.button("📋 Generate My Nutrition Summary", key="btn_gen_summary_main", use_container_width=True)
    if gen_summary_btn:
        user_has_messages = any(msg["role"] == "user" for msg in st.session_state.messages)
        if not user_has_messages:
            st.warning("⚠️ No meal entries yet! Describe a meal or upload a food photo first.")
        else:
            client = get_gemini_client()
            with st.spinner("Generating your nutrition summary..."):
                try:
                    summary_text = generate_nutrition_summary(client, st.session_state.messages)
                    st.session_state.nutrition_summary = summary_text
                    st.session_state.wa_send_status = None
                except Exception as err:
                    st.error(f"⚠️ Failed to generate summary: {str(err)}")
            st.rerun()

    # --- Food Image Upload Expander ---
    with st.expander("📸 Upload Food Photo for Analysis", expanded=False):
        uploaded_file = st.file_uploader(
            "Upload meal photo (JPG, PNG, WEBP)",
            type=list(ALLOWED_EXTENSIONS),
            key=f"uploader_{st.session_state.uploader_key}",
            help="Supports JPG, JPEG, PNG, and WEBP formats",
        )
        if uploaded_file is not None:
            st.image(uploaded_file, caption="Selected image preview", width=250)

    # --- Chat Input ---
    user_text_input = st.chat_input("Describe a meal or ask a question about your food photo…")

    # --- Determine if a turn was submitted ---
    turn_submitted = False
    process_image_bytes = None
    process_mime_type = None
    final_text_prompt = ""

    if user_text_input is not None:
        turn_submitted = True
        final_text_prompt = user_text_input.strip()

    if uploaded_file is not None and not user_text_input:
        analyze_photo_btn = st.button("Analyze Uploaded Photo 🥗", use_container_width=True)
        if analyze_photo_btn:
            turn_submitted = True
            final_text_prompt = (
                "Please analyze this food photo: identify visible items, "
                "estimate serving sizes, calories, protein, carbohydrates, and fat."
            )

    if turn_submitted:
        # --- Handle image validation & extraction if present ---
        if uploaded_file is not None:
            ext = uploaded_file.name.lower().split(".")[-1]
            if ext not in ALLOWED_EXTENSIONS:
                st.error(
                    f"⚠️ Unsupported image extension '.{ext}'. "
                    "Please upload a JPG, PNG, or WEBP image."
                )
                st.stop()

            raw_mime = uploaded_file.type or f"image/{'jpeg' if ext in ['jpg', 'jpeg'] else ext}"
            if raw_mime not in ALLOWED_IMAGE_TYPES and ext not in ALLOWED_EXTENSIONS:
                st.error("⚠️ Unsupported image format. Please upload a valid food image.")
                st.stop()

            try:
                process_image_bytes = uploaded_file.read()
                process_mime_type = ALLOWED_IMAGE_TYPES.get(raw_mime, f"image/{ext if ext != 'jpg' else 'jpeg'}")
            except Exception as err:
                st.error(f"⚠️ Failed to read uploaded image file: {str(err)}")
                st.stop()

        # Check if we have at least text or image
        if not final_text_prompt and not process_image_bytes:
            st.warning("Please provide a text prompt or select an image to analyze.")
            st.stop()

        # Add user message to session state
        user_msg = {
            "role": "user",
            "content": final_text_prompt,
            "image_bytes": process_image_bytes,
            "mime_type": process_mime_type,
        }
        st.session_state.messages.append(user_msg)

        # Increment uploader_key so file uploader widget clears on next render
        st.session_state.uploader_key += 1

        # Render the newly added user message
        with st.chat_message("user"):
            if process_image_bytes:
                st.image(process_image_bytes, caption="Uploaded Food Photo 📸", width=320)
            if final_text_prompt:
                st.markdown(final_text_prompt)

        # --- Call Gemini API ---
        client = get_gemini_client()
        with st.chat_message("assistant"):
            with st.spinner("MacroSnap is analyzing your food..."):
                try:
                    reply_text = call_gemini(client, st.session_state.messages)
                except Exception as e:
                    reply_text = (
                        "⚠️ Sorry, MacroSnap could not analyze your request right now. "
                        f"Error details: {str(e)}"
                    )

            st.markdown(reply_text)

        # Store assistant response in session state
        st.session_state.messages.append(
            {
                "role": "assistant",
                "content": reply_text,
                "image_bytes": None,
                "mime_type": None,
            }
        )

        st.rerun()
