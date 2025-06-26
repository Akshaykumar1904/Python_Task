import streamlit as st
import requests
import json
from datetime import datetime
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
    
    .available-slots {
        background-color: #e3f2fd;
        border: 1px solid #bbdefb;
        color: #0d47a1;
        padding: 1rem;
        border-radius: 5px;
        margin: 1rem 0;
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
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Error communicating with the booking agent: {str(e)}")
        return None


def get_appointments():
    """Get all appointments from the API"""
    try:
        response = requests.get(f"{API_BASE_URL}/appointments")
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching appointments: {str(e)}")
        return None


# Main app layout
st.markdown(
    '<h1 class="main-header">🤖 AI Calendar Booking Assistant</h1>',
    unsafe_allow_html=True,
)

# Create two columns
col1, col2 = st.columns([2, 1])

with col1:
    st.markdown("### 💬 Chat with the Booking Assistant")

    # Chat interface
    with st.container():
        # Display conversation history
        if st.session_state.messages:
            st.markdown('<div class="chat-container">', unsafe_allow_html=True)
            for i, message in enumerate(st.session_state.messages):
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
                "👋 Welcome! I'm your AI booking assistant. You can say things like:\n"
                "- 'I'd like to book a meeting tomorrow afternoon'\n"
                "- 'What slots are available next week?'\n"
                "- 'Schedule a consultation for Monday morning'"
            )

    # Chat input
    with st.form("chat_form", clear_on_submit=True):
        user_input = st.text_input(
            "Type your message here...",
            placeholder="e.g., I'd like to book a meeting tomorrow at 2 PM",
            key="user_input",
        )
        send_button = st.form_submit_button("Send 📤")

        if send_button and user_input.strip():
            # Add user message to session state
            st.session_state.messages.append({"role": "user", "content": user_input})

            # Send to API
            with st.spinner("🤔 Processing your request..."):
                api_response = send_message_to_api(user_input)

            if api_response:
                # Add AI response to session state
                st.session_state.messages.append(
                    {"role": "assistant", "content": api_response["response"]}
                )

                # Update booking status
                if api_response.get("booking_confirmed"):
                    st.session_state.booking_confirmed = True

                # Rerun to update the display
                st.rerun()

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
                start_time = datetime.fromisoformat(apt["start"].replace("Z", "+00:00"))
                end_time = datetime.fromisoformat(apt["end"].replace("Z", "+00:00"))

                st.write(
                    f"**Start:** {start_time.strftime('%A, %B %d, %Y at %I:%M %p')}"
                )
                st.write(f"**End:** {end_time.strftime('%A, %B %d, %Y at %I:%M %p')}")
                st.write(f"**ID:** {apt['id']}")
    else:
        st.info("No appointments scheduled yet.")

    # Quick actions
    st.markdown("### ⚡ Quick Actions")

    if st.button("🗓️ Check This Week's Availability"):
        # Add message to trigger availability check
        st.session_state.messages.append(
            {"role": "user", "content": "What slots are available this week?"}
        )

        with st.spinner("Checking availability..."):
            api_response = send_message_to_api("What slots are available this week?")

        if api_response:
            st.session_state.messages.append(
                {"role": "assistant", "content": api_response["response"]}
            )
            st.rerun()

    if st.button("📞 Book Quick Call"):
        st.session_state.messages.append(
            {
                "role": "user",
                "content": "I'd like to schedule a quick call for tomorrow",
            }
        )

        with st.spinner("Finding available slots..."):
            api_response = send_message_to_api(
                "I'd like to schedule a quick call for tomorrow"
            )

        if api_response:
            st.session_state.messages.append(
                {"role": "assistant", "content": api_response["response"]}
            )
            st.rerun()

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
    **Natural Language Examples:**
    - "Book a meeting tomorrow at 2 PM"
    - "I need a consultation next week"
    - "What's available on Monday?"
    - "Schedule a call for Thursday morning"
    - "Can we meet Friday afternoon?"
    
    **Features:**
    - 🗣️ Natural conversation
    - 📅 Real-time availability check
    - ⏰ Smart time slot suggestions
    - ✅ Instant booking confirmation
    - 📱 Mobile-friendly interface
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

    st.markdown(
        f"**Backend:** FastAPI  \n**Agent:** LangGraph  \n**Frontend:** Streamlit"
    )

    if st.button("🔄 Reset Conversation"):
        st.session_state.conversation_id = str(uuid.uuid4())
        st.session_state.messages = []
        st.session_state.booking_confirmed = False
        st.rerun()
