# 🥗 MacroSnap — AI Nutrition Buddy

**MacroSnap** is an interactive AI nutrition buddy built with Streamlit, Google Gemini 2.5 Flash, and Twilio WhatsApp. It helps users track their daily meals, analyze food photos, estimate calories and macronutrients in plain language, and receive nutrition summaries directly on their phone.

---

## ✨ Features

- 👤 **Personalized Onboarding**: Sign in with your name and WhatsApp number.
- 💬 **Interactive AI Chat**: Describe meals in natural text (e.g., *"I ate 2 eggs and 2 slices of toast for breakfast"*).
- 📸 **Multimodal Food Photo Analysis**: Upload meal photos (`JPG`, `PNG`, `WEBP`) for automatic food identification and visual macro estimations.
- 🧠 **Context-Aware Multi-turn Memory**: Remembers meal history so you can ask follow-up questions (e.g., *"Which meal had the most protein?"*).
- 📋 **Nutrition Summary Generation**: One-click generation of structured daily calorie & macronutrient totals.
- 📱 **Twilio WhatsApp Integration**: Receive meal summary notifications delivered straight to your WhatsApp handset via Twilio Sandbox.
- 🔒 **Security-First Architecture**: Strictly zero hardcoded keys or credentials; secrets are safely stored in Streamlit secrets management.

---

## 🛠️ Technology Stack

- **Frontend / Framework**: [Streamlit](https://streamlit.io/)
- **AI Model & SDK**: Google Gemini 2.5 Flash via [`google-genai`](https://pypi.org/project/google-genai/)
- **Messaging API**: [Twilio WhatsApp API](https://www.twilio.com/docs/whatsapp) via [`twilio`](https://pypi.org/project/twilio/)
- **Language**: Python 3.10+

---

## 🚀 How the Application Works

1. **User Onboarding**: The user signs in with their name and WhatsApp number.
2. **Meal Entry**: The user can type meal descriptions or upload a photo of their plate.
3. **AI Analysis**: Gemini 2.5 Flash analyzes text or multimodal image inputs against the system instructions defined in `prompts.py`.
4. **Summary & Delivery**: Click **"Generate My Nutrition Summary"** to compile daily totals, then click **"Send to WhatsApp"** to dispatch the notification via Twilio.

---

## 💻 Installation & Local Setup

### 1. Prerequisites
- Python 3.10+ installed on your system.
- A Google Gemini API Key from [Google AI Studio](https://aistudio.google.com/).
- A Twilio Account SID, Auth Token, and WhatsApp Sandbox number from [Twilio Console](https://www.twilio.com/console).

### 2. Clone the Repository
```bash
git clone https://github.com/AdarshGaddameedi25/MacroSnap.git
cd MacroSnap
```

### 3. Create & Activate a Virtual Environment
```bash
# On Windows
python -m venv venv
.\venv\Scripts\activate

# On macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

### 4. Install Dependencies
```bash
pip install -r requirements.txt
```

---

## 🔐 Secrets Configuration

1. Create a `.streamlit` folder if it doesn't exist:
   ```bash
   mkdir .streamlit
   ```

2. Copy the example secrets file:
   ```bash
   cp .streamlit/secrets.toml.example .streamlit/secrets.toml
   ```

3. Open `.streamlit/secrets.toml` and fill in your credentials:
   ```toml
   GEMINI_API_KEY = "YOUR_ACTUAL_GEMINI_API_KEY"

   TWILIO_ACCOUNT_SID = "YOUR_ACTUAL_TWILIO_ACCOUNT_SID"
   TWILIO_AUTH_TOKEN = "YOUR_ACTUAL_TWILIO_AUTH_TOKEN"
   TWILIO_WHATSAPP_FROM = "whatsapp:+17372508034"
   TWILIO_CONTENT_SID = "YOUR_ACTUAL_TWILIO_CONTENT_SID"
   ```

> ⚠️ **SECURITY NOTE**: Never commit `.streamlit/secrets.toml` or any file containing API keys/tokens to Git. Ensure `.streamlit/secrets.toml` is listed in your `.gitignore`.

---

## 🏃 Running the Application Locally

Start the Streamlit application using:
```bash
streamlit run app.py
```

The application will automatically open in your default browser at `http://localhost:8501`.

---

## 📁 Project Structure

```
MacroSnap/
├── app.py                      # Main Streamlit application logic
├── prompts.py                  # System prompts and prompt templates
├── requirements.txt            # Project dependencies (streamlit, google-genai, twilio)
├── .gitignore                  # Git ignore rules for secrets and virtualenvs
├── README.md                   # Project documentation
└── .streamlit/
    ├── secrets.toml.example    # Example secrets configuration template
    └── secrets.toml            # Private local secrets (ignored by Git)
```

---

## 👤 Author & Project Info

- **Project**: MacroSnap — AI Nutrition Buddy
- **Author**: [Adarsh Gaddameedi](https://github.com/AdarshGaddameedi25)
- **Repository**: [https://github.com/AdarshGaddameedi25/MacroSnap](https://github.com/AdarshGaddameedi25/MacroSnap)
