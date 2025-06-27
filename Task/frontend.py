import streamlit as st
import requests
import json
from datetime import datetime, timedelta
import uuid

# Page config
st.set_page_config(
    page_title="AI Calendar Booking Assistant", page_icon="📅", layout="wide"
)

# API Configuration
API_BASE_URL = "http://localhost:8000"

# Initialize session state
if "conversation_id" not in st.session_state:
    st.session_state.conversation_id = str(uuid.uuid4())

if "messages" not in st.session_state:
    st.session_state.messages = []

if "booking_confirmed" not in st.session_state:
    st.session_state.booking_confirmed = False

if "awaiting_confirmation" not in st.session_state:
    st.session_state.awaiting_confirmation = False

if "selected_slot" not in st.session_state:
    st.session_state.selected_slot = None

# Custom CSS for better styling
st.markdown(
    """
<style>
    .main-header {
        text-align: center;
        color: #1f77b4;
        margin-bottom: 2rem;
    }
    
    .chat-container {
        max-height: 500px;
        overflow-y: auto;
        padding: 1rem;
        border: 1px solid #e0e0e0;
        border-radius: 10px;
        background-color: #f8f9fa;
    }
    
    .user-message {
        background-color: #007bff;
        color: white;
        padding: 0.5rem 1rem;
        border-radius: 15px;
        margin: 0.5rem 0;
        text-align: right;
        margin-left: 20%;
    }
    
    .ai-message {
        background-color: #28a745;
        color: white;
        padding: 0.5rem 1rem;
        border-radius: 15px;
        margin: 0.5rem 0;
        margin-right: 20%;
    }
    
    .booking-success {
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        color: #155724;
        padding: 1rem;
        border-radius: 5px;
        margin: 1rem 0;
    }
    
    .quick-phrases {
        background-color: #471396;
        border: 1px solid #ffeaa7;
        color: #DCD7C9;
        padding: 1rem;
        border-radius: 5px;
        margin: 1rem 0;
    }
    
    .stButton > button {
        width: 100%;
        margin: 0.2rem 0;
    }
</style>
""",
    unsafe_allow_html=True,
)


def send_message_to_api(message: str) -> dict:
    """Send message to the FastAPI backend"""
    try:
        response = requests.post(
            f"{API_BASE_URL}/chat",
            json={
                "message": message,
                "conversation_id": st.session_state.conversation_id,
            },
            headers={"Content-Type": "application/json"},
            timeout=30,
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Error communicating with the booking agent: {str(e)}")
        return None


def get_appointments():
    """Get all appointments from the API"""
    try:
        response = requests.get(f"{API_BASE_URL}/appointments", timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching appointments: {str(e)}")
        return None


def send_predefined_message(message: str):
    """Send a predefined message and handle the response"""
    st.session_state.messages.append({"role": "user", "content": message})

    with st.spinner("🤔 Processing your request..."):
        api_response = send_message_to_api(message)

    if api_response:
        st.session_state.messages.append(
            {"role": "assistant", "content": api_response["response"]}
        )

        # Check if slots are available for selection
        if api_response.get("available_slots"):
            st.session_state.awaiting_confirmation = True

        if api_response.get("booking_confirmed"):
            st.session_state.booking_confirmed = True
            st.session_state.awaiting_confirmation = False

        st.rerun()


# Main app layout
st.markdown(
    '<h1 class="main-header">🤖 AI Calendar Booking Assistant</h1>',
    unsafe_allow_html=True,
)

# Create two columns
col1, col2 = st.columns([2, 1])

with col1:
    st.markdown("### 💬 Chat with the Booking Assistant")

    # Display conversation history
    if st.session_state.messages:
        st.markdown('<div class="chat-container">', unsafe_allow_html=True)
        for message in st.session_state.messages:
            if message["role"] == "user":
                st.markdown(
                    f'<div class="user-message">{message["content"]}</div>',
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    f'<div class="ai-message">{message["content"]}</div>',
                    unsafe_allow_html=True,
                )
        st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.info(
            "👋 Welcome! I'm your AI booking assistant. Use the quick phrases below to get started!"
        )

    # Quick Phrases Section
    st.markdown(
        """
    <div class="quick-phrases">
        <h4>🎯 Quick Phrases - Click the buttons below instead of typing:</h4>
        <p>These phrases work best with the booking system!</p>
    </div>
    """,
        unsafe_allow_html=True,
    )

    # Quick phrase buttons in columns
    phrase_col1, phrase_col2 = st.columns(2)

    with phrase_col1:
        st.markdown("**📅 Booking Requests:**")
        if st.button("📝 Book a meeting tomorrow"):
            send_predefined_message("book a meeting tomorrow")

        if st.button("📞 Schedule a call tomorrow"):
            send_predefined_message("schedule a call tomorrow")

        if st.button("🤝 Book appointment tomorrow"):
            send_predefined_message("book appointment tomorrow")

        if st.button("📅 Book meeting next week"):
            send_predefined_message("book meeting next week")

    with phrase_col2:
        st.markdown("**🔍 Availability Checks:**")
        if st.button("⏰ What slots are available tomorrow"):
            send_predefined_message("what slots are available tomorrow")

        if st.button("📋 Check availability next week"):
            send_predefined_message("check availability next week")

        if st.button("🗓️ Show me free times"):
            send_predefined_message("show me available slots")

        if st.button("⌚ What times are free"):
            send_predefined_message("what times are available")

    # Time-specific booking buttons
    st.markdown("**🕐 Specific Time Requests:**")
    time_col1, time_col2, time_col3 = st.columns(3)

    with time_col1:
        if st.button("🌅 Book meeting tomorrow morning"):
            send_predefined_message("book meeting tomorrow morning")

        if st.button("🌞 Book meeting tomorrow afternoon"):
            send_predefined_message("book meeting tomorrow afternoon")

    with time_col2:
        if st.button("🕙 Book meeting tomorrow at 10 am"):
            send_predefined_message("book meeting tomorrow at 10 am")

        if st.button("🕐 Book meeting tomorrow at 2 pm"):
            send_predefined_message("book meeting tomorrow at 2 pm")

    with time_col3:
        if st.button("📅 Book meeting monday"):
            send_predefined_message("book meeting monday")

        if st.button("📅 Book meeting friday"):
            send_predefined_message("book meeting friday")

    # Slot selection buttons (show when awaiting confirmation)
    if st.session_state.awaiting_confirmation:
        st.markdown("**✅ Confirm Your Selection:**")
        confirm_col1, confirm_col2, confirm_col3, confirm_col4 = st.columns(4)

        with confirm_col1:
            if st.button("✅ Select slot 1"):
                send_predefined_message("1")

        with confirm_col2:
            if st.button("✅ Select slot 2"):
                send_predefined_message("2")

        with confirm_col3:
            if st.button("✅ Select slot 3"):
                send_predefined_message("3")

        with confirm_col4:
            if st.button("✅ Select slot 4"):
                send_predefined_message("4")

        # Additional confirmation phrases
        st.markdown("**Or use these confirmation phrases:**")
        confirm_row1, confirm_row2 = st.columns(2)

        with confirm_row1:
            if st.button("✅ Yes, confirm booking"):
                send_predefined_message("yes confirm booking")

            if st.button("✅ That works for me"):
                send_predefined_message("that works")

        with confirm_row2:
            if st.button("✅ Sounds good"):
                send_predefined_message("sounds good")

            if st.button("✅ Confirm"):
                send_predefined_message("confirm")

    # Manual input (kept as backup)
    st.markdown("---")
    st.markdown("**💬 Or type manually (use phrases similar to buttons above):**")

    with st.form("chat_form", clear_on_submit=True):
        user_input = st.text_input(
            "Type your message here...",
            placeholder="e.g., book meeting tomorrow or check availability next week",
            key="user_input",
        )
        send_button = st.form_submit_button("Send 📤")

        if send_button and user_input.strip():
            send_predefined_message(user_input)

    # Show booking confirmation
    if st.session_state.booking_confirmed:
        st.markdown(
            """
    <div class="booking-success">
        <h4>✅ Booking Confirmed!</h4>
        <p>Your appointment has been successfully booked. Check the appointments panel for details.</p>
    </div>
    """,
            unsafe_allow_html=True,
        )
        st.session_state.booking_confirmed = False  # Reset after display
        st.rerun()  # 👈 force refresh so new appointment appears

with col2:
    st.markdown("### 📅 Current Appointments")

    # Refresh button
    if st.button("🔄 Refresh Appointments"):
        st.rerun()

    # Display appointments
    appointments_data = get_appointments()
    if appointments_data and appointments_data.get("appointments"):
        appointments = appointments_data["appointments"]

        for apt in appointments:
            with st.expander(f"📋 {apt['title']}", expanded=False):
                try:
                    if isinstance(apt["start"], str):
                        start_time = datetime.fromisoformat(
                            apt["start"].replace("Z", "+00:00")
                        )
                        end_time = datetime.fromisoformat(
                            apt["end"].replace("Z", "+00:00")
                        )
                    else:
                        start_time = apt["start"]
                        end_time = apt["end"]

                    st.write(
                        f"**Start:** {start_time.strftime('%A, %B %d, %Y at %I:%M %p')}"
                    )
                    st.write(
                        f"**End:** {end_time.strftime('%A, %B %d, %Y at %I:%M %p')}"
                    )
                    st.write(f"**ID:** {apt['id']}")
                except Exception as e:
                    st.write(f"**Start:** {apt['start']}")
                    st.write(f"**End:** {apt['end']}")
                    st.write(f"**ID:** {apt['id']}")
    else:
        st.info("No appointments scheduled yet.")

# Footer
st.markdown("---")
st.markdown(
    """
<div style="text-align: center; color: #666;">
    <small>
        🤖 Powered by FastAPI + LangGraph + Streamlit | 
        <strong>Conversation ID:</strong> {conversation_id}
    </small>
</div>
""".format(
        conversation_id=st.session_state.conversation_id[:8]
    ),
    unsafe_allow_html=True,
)

# Sidebar with instructions
with st.sidebar:
    st.markdown("## 📖 How to Use")
    st.markdown(
        """
    **✅ RECOMMENDED - Use Quick Phrase Buttons:**
    - Click the buttons instead of typing
    - These phrases work best with the AI
    - Covers all booking scenarios
    
    **🎯 Proven Working Phrases:**
    - "book meeting tomorrow"
    - "schedule call tomorrow" 
    - "check availability next week"
    - "what slots are available"
    - Numbers: "1", "2", "3", "4" for slot selection
    - "confirm", "yes", "sounds good"
    
    **⚠️ Avoid Complex Language:**
    - Don't use: "I would like to schedule..."
    - Use: "book meeting tomorrow"
    - Don't use: "Can we meet on..."
    - Use: "book meeting monday"
    """
    )

    st.markdown("---")
    st.markdown("## 🔧 System Status")

    # Check API health
    try:
        health_response = requests.get(f"{API_BASE_URL}/health", timeout=5)
        if health_response.status_code == 200:
            st.success("✅ API Connected")
        else:
            st.error("❌ API Error")
    except:
        st.error("❌ API Offline")

    st.markdown("---")
    st.markdown("## 🎯 Booking Tips")
    st.markdown(
        """
    **Step 1:** Click a booking button  
    **Step 2:** Wait for available slots  
    **Step 3:** Click slot number (1, 2, 3, 4)  
    **Step 4:** Confirm with "yes" or "confirm"
    
    **Most reliable phrases:**
    - book meeting tomorrow
    - check availability tomorrow  
    - 1 (for first slot)
    - confirm
    """
    )

    if st.button("🔄 Reset Conversation"):
        st.session_state.conversation_id = str(uuid.uuid4())
        st.session_state.messages = []
        st.session_state.booking_confirmed = False
        st.session_state.awaiting_confirmation = False
        st.session_state.selected_slot = None
        st.rerun()
