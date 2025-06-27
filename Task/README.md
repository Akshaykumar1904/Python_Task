# 📅 AI Calendar Booking Assistant

An intelligent appointment booking assistant powered by **FastAPI**, **LangGraph**, and **Streamlit**. It can understand natural language queries like _"book a meeting tomorrow"_ or _"what slots are available on Friday"_ and guide the user through slot selection and confirmation.

---

## 🚀 Features

- 🧠 Natural Language Booking using LangGraph + LLM-powered intent detection
- 📆 Smart Slot Suggestions based on your availability
- ✅ Interactive Booking Flow with confirmation and feedback
- 💬 Live Chat Interface with Quick Phrase buttons
- 🔎 View & Manage Appointments
- 🌐 API-first Backend with real-time updates

---

## 🧰 Tech Stack

- **Frontend**: Streamlit (Chat UI)
- **Backend**: FastAPI + LangGraph
- **Calendar**: In-memory mock (`MockCalendar`)
- **AI Logic**: LangGraph (stateful workflow)
- **Styling**: Custom CSS for Streamlit

---

## 📁 Project Structure

```
📦python/task/
├── backend.py     # FastAPI + LangGraph booking logic
├── frontend.py    # Streamlit UI for chat and slots
├── .gitignore
├── requirements.txt
└── README.md
```

---

## Setup Instructions

### INSTALL REQUIREMENTS

```bash
pip install -r requirements.txt
```

---

### Start Backend

```bash
python -m uvicorn backend:app --reload
# Runs on http://localhost:8000
```

---

### Start Frontend

```bash
python -m streamlit run frontend.py
```

---

### Gitignore

```
__pycache__/
*.pyc
*.pyo
venv/
.env
```

---

### Future Improvements

-OAuth login & calendar integration (Google, Outlook)

- Persistent DB (PostgreSQL or MongoDB)

- Voice input

- Email/SMS reminders

---

### Author

Made with ❤️ by Akshay Kumar-
Your friendly AI appointment agent!
