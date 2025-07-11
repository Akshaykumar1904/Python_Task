from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import json
import re
from langchain_core.messages import HumanMessage, AIMessage
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict
import asyncio


class MockCalendar:
    def __init__(self):
        self.appointments = [
            {
                "id": "1",
                "title": "Team Meeting",
                "start": datetime.now() + timedelta(days=1, hours=2),
                "end": datetime.now() + timedelta(days=1, hours=3),
            },
            {
                "id": "2",
                "title": "Client Call",
                "start": datetime.now() + timedelta(days=2, hours=4),
                "end": datetime.now() + timedelta(days=2, hours=5),
            },
        ]

    def get_availability(self, start_date: datetime, end_date: datetime) -> List[Dict]:
        available_slots = []
        current = start_date

        while current < end_date:
            # Only business hours (9 AM to 5 PM)
            if 9 <= current.hour < 17 and current.weekday() < 5:  # Monday to Friday
                slot_end = current + timedelta(hours=1)
                conflict = False

                # Check for conflicts with existing appointments
                for apt in self.appointments:
                    apt_start = apt["start"]
                    apt_end = apt["end"]
                    if current < apt_end and slot_end > apt_start:
                        conflict = True
                        break

                if not conflict:
                    available_slots.append(
                        {
                            "start": current.isoformat(),  # Convert to ISO string immediately
                            "end": slot_end.isoformat(),   # Convert to ISO string immediately
                            "formatted": current.strftime("%A, %B %d at %I:%M %p"),
                            "_datetime_start": current,    # Keep datetime for internal use
                            "_datetime_end": slot_end,     # Keep datetime for internal use
                        }
                    )
            current += timedelta(hours=1)

        return available_slots[:10]  # Return max 10 slots

    def book_appointment(
        self, title: str, start: datetime, duration_hours: int = 1
    ) -> Dict:
        appointment = {
            "id": str(len(self.appointments) + 1),
            "title": title,
            "start": start,
            "end": start + timedelta(hours=duration_hours),
        }
        self.appointments.append(appointment)
        return appointment


calendar = MockCalendar()


class ConversationState(TypedDict):
    messages: List[Any]
    user_intent: str
    extracted_info: Dict[str, Any]
    available_slots: List[Dict]
    selected_slot: Optional[Dict]
    booking_confirmed: bool
    conversation_phase: str  # Added to track conversation phase


class ChatMessage(BaseModel):
    message: str
    conversation_id: str


class ChatResponse(BaseModel):
    response: str
    available_slots: List[Dict] = []
    booking_confirmed: bool = False
    conversation_id: str


def extract_date_time_info(text: str) -> Dict[str, Any]:
    """Extract date and time information from text"""
    info = {}
    text_lower = text.lower()

    # Date patterns
    date_patterns = {
        r"tomorrow": "tomorrow",
        r"next week": "next_week",
        r"monday": "monday",
        r"tuesday": "tuesday",
        r"wednesday": "wednesday",
        r"thursday": "thursday",
        r"friday": "friday",
        r"saturday": "saturday",
        r"sunday": "sunday",
    }

    for pattern, value in date_patterns.items():
        if re.search(pattern, text_lower):
            info["date_preference"] = value
            break

    # Time patterns
    time_patterns = [
        (r"(\d{1,2})\s*(am|pm)", "specific_time"),
        (r"(\d{1,2}):(\d{2})\s*(am|pm)", "specific_time"),
        (r"morning", "morning"),
        (r"afternoon", "afternoon"),
        (r"evening", "evening"),
    ]

    for pattern, time_type in time_patterns:
        match = re.search(pattern, text_lower)
        if match:
            info["time_preference"] = (
                match.group() if time_type == "specific_time" else time_type
            )
            break

    # Purpose keywords
    purpose_keywords = [
        "meeting",
        "consultation",
        "call",
        "interview",
        "demo",
        "appointment",
    ]
    for keyword in purpose_keywords:
        if keyword in text_lower:
            info["purpose"] = keyword
            break

    return info


def determine_intent(text: str, conversation_phase: str = "") -> str:
    """Determine user intent from text with context"""
    text_lower = text.lower().strip()

    print(f"DEBUG: Determining intent for: '{text_lower}', phase: '{conversation_phase}'")

    # Check for slot selection (numbers) - only if we're in slot selection phase
    if conversation_phase == "awaiting_slot_selection" and text_lower in ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10"]:
        return "select_slot"

    # Check for confirmation - prioritize if we have a selected slot
    if conversation_phase == "awaiting_confirmation" and any(
        word in text_lower
        for word in ["confirm", "yes", "sounds good", "that works", "book it", "ok"]
    ):
        return "confirm_booking"

    # Check for booking request
    if any(
        word in text_lower for word in ["book", "schedule", "appointment", "meeting"]
    ):
        return "book_appointment"

    # Check for availability
    if any(
        word in text_lower
        for word in ["available", "free", "slots", "times", "check availability", "show me"]
    ):
        return "check_availability"

    # Check for cancellation/modification
    if any(word in text_lower for word in ["cancel", "change", "reschedule"]):
        return "modify_booking"

    return "general_inquiry"


def get_date_range_from_preference(preference: str) -> tuple:
    """Get date range based on user preference"""
    now = datetime.now()

    if preference == "tomorrow":
        start = (now + timedelta(days=1)).replace(
            hour=9, minute=0, second=0, microsecond=0
        )
        end = start.replace(hour=17)
    elif preference == "next_week":
        days_ahead = 7 - now.weekday()
        start = (now + timedelta(days=days_ahead)).replace(
            hour=9, minute=0, second=0, microsecond=0
        )
        end = start + timedelta(days=4, hours=8)  # Mon-Fri
    elif preference in [
        "monday",
        "tuesday",
        "wednesday",
        "thursday",
        "friday",
        "saturday",
        "sunday",
    ]:
        weekdays = [
            "monday",
            "tuesday",
            "wednesday",
            "thursday",
            "friday",
            "saturday",
            "sunday",
        ]
        target_weekday = weekdays.index(preference)
        days_ahead = target_weekday - now.weekday()
        if days_ahead <= 0:  # Target day already happened this week
            days_ahead += 7
        start = (now + timedelta(days=days_ahead)).replace(
            hour=9, minute=0, second=0, microsecond=0
        )
        end = start.replace(hour=17)
    else:
        # Default: next business day
        start = (now + timedelta(days=1)).replace(
            hour=9, minute=0, second=0, microsecond=0
        )
        end = start + timedelta(days=2, hours=8)

    return start, end


def analyze_input(state: ConversationState) -> ConversationState:
    """Analyze user input and extract intent and information"""
    last_message = state["messages"][-1].content
    conversation_phase = state.get("conversation_phase", "")
    
    intent = determine_intent(last_message, conversation_phase)
    extracted_info = extract_date_time_info(last_message)

    state["user_intent"] = intent
    state["extracted_info"] = {**state.get("extracted_info", {}), **extracted_info}

    print(f"DEBUG: Intent determined: {intent}, Phase: {conversation_phase}")
    
    return state


def check_availability(state: ConversationState) -> ConversationState:
    """Check available time slots"""
    extracted_info = state["extracted_info"]

    if "date_preference" in extracted_info:
        start_date, end_date = get_date_range_from_preference(
            extracted_info["date_preference"]
        )
    else:
        # Default to tomorrow
        now = datetime.now()
        start_date = (now + timedelta(days=1)).replace(
            hour=9, minute=0, second=0, microsecond=0
        )
        end_date = start_date.replace(hour=17)

    available_slots = calendar.get_availability(start_date, end_date)
    state["available_slots"] = available_slots
    state["conversation_phase"] = "awaiting_slot_selection"  # Set phase

    print(f"DEBUG: Found {len(available_slots)} available slots")
    
    return state


def handle_slot_selection(state: ConversationState) -> ConversationState:
    """Handle user's slot selection"""
    last_message = state["messages"][-1].content.strip()
    available_slots = state.get("available_slots", [])

    print(f"DEBUG: Handling slot selection: '{last_message}', Available slots: {len(available_slots)}")

    # Handle numeric selection
    try:
        slot_number = int(last_message)
        if 1 <= slot_number <= len(available_slots):
            selected_slot = available_slots[slot_number - 1].copy()
            state["selected_slot"] = selected_slot
            state["conversation_phase"] = "awaiting_confirmation"  # Update phase
            print(f"DEBUG: Slot {slot_number} selected: {selected_slot['formatted']}")
        else:
            print(f"DEBUG: Invalid slot number: {slot_number}")
    except ValueError:
        print(f"DEBUG: Could not parse slot number from: '{last_message}'")

    return state


def confirm_booking(state: ConversationState) -> ConversationState:
    """Confirm and create the booking"""
    selected_slot = state.get("selected_slot")
    extracted_info = state.get("extracted_info", {})

    print(f"DEBUG: Confirming booking. Selected slot: {selected_slot}")

    if selected_slot:
        purpose = extracted_info.get("purpose", "meeting")
        title = f"Scheduled {purpose.title()}"

        try:
            # Use the datetime object for booking
            start_datetime = selected_slot.get("_datetime_start")
            if not start_datetime:
                # Fallback: parse from ISO string
                start_datetime = datetime.fromisoformat(selected_slot["start"].replace("Z", "+00:00"))

            appointment = calendar.book_appointment(title, start_datetime)

            state["booking_confirmed"] = True
            state["available_slots"] = []  # Reset slots after booking
            state["selected_slot"] = None  # Clear selected slot
            state["user_intent"] = ""  # Reset intent
            state["conversation_phase"] = "booking_complete"  # Update phase

            response = f"✅ Booking confirmed! Your {purpose} is scheduled for {selected_slot['formatted']}. Appointment ID: {appointment['id']}"
            state["messages"].append(AIMessage(content=response))

            print(f"DEBUG: Appointment booked successfully: {appointment}")

        except Exception as e:
            print(f"ERROR: Failed to book appointment: {str(e)}")
            response = "❌ Sorry, there was an error booking your appointment. Please try again."
            state["messages"].append(AIMessage(content=response))
    else:
        response = "❌ No slot selected. Please choose a slot first."
        state["messages"].append(AIMessage(content=response))

    return state


def generate_response(state: ConversationState) -> ConversationState:
    """Generate appropriate response based on intent and state"""
    intent = state["user_intent"]
    available_slots = state.get("available_slots", [])
    extracted_info = state.get("extracted_info", {})
    selected_slot = state.get("selected_slot")
    conversation_phase = state.get("conversation_phase", "")

    print(f"DEBUG: Generating response for intent: {intent}, phase: {conversation_phase}")
    print(f"DEBUG: Available slots: {len(available_slots)}, Selected slot: {bool(selected_slot)}")

    if intent == "book_appointment" or intent == "check_availability":
        if available_slots:
            response = "I found some available time slots for you:\n\n"
            for i, slot in enumerate(available_slots, 1):
                response += f"{i}. {slot['formatted']}\n"
            response += "\nPlease select a slot by clicking the button or typing the number (e.g., '1' for the first slot)."
            # Don't change phase here - it's already set in check_availability
        else:
            response = "Let me check availability for you. Please specify your preferred date and time."

    elif intent == "select_slot":
        if selected_slot:
            response = f"Perfect! You've selected: {selected_slot['formatted']}\n\nWould you like to confirm this booking? Click 'Confirm' or reply with 'yes'."
            # Phase is already set to awaiting_confirmation in handle_slot_selection
        else:
            response = "I didn't find that slot. Please choose a number from the available options above."

    elif intent == "confirm_booking":
        # This should be handled by confirm_booking function, but this is a fallback
        if selected_slot:
            response = "Processing your booking confirmation..."
        else:
            response = "Please select a time slot first before confirming."

    else:  # general_inquiry
        response = "Hello! I'm here to help you book appointments. You can say things like:\n- 'book meeting tomorrow'\n- 'check availability next week'\n- 'schedule call monday'"
        state["conversation_phase"] = "initial"

    state["messages"].append(AIMessage(content=response))
    return state


def create_booking_workflow():
    """Create the booking workflow"""
    workflow = StateGraph(ConversationState)

    # Add nodes
    workflow.add_node("analyze", analyze_input)
    workflow.add_node("check_availability", check_availability)
    workflow.add_node("handle_selection", handle_slot_selection)
    workflow.add_node("respond", generate_response)
    workflow.add_node("confirm_booking", confirm_booking)

    # Set entry point
    workflow.set_entry_point("analyze")

    def should_check_availability(state):
        intent = state["user_intent"]
        print(f"DEBUG: Routing decision for intent: {intent}")

        if intent in ["book_appointment", "check_availability"]:
            return "check_availability"
        elif intent == "select_slot":
            return "handle_selection"
        elif intent == "confirm_booking":
            # Check if we have a selected slot to confirm
            if state.get("selected_slot"):
                return "confirm_booking"
            else:
                return "respond"
        else:
            return "respond"

    # Add conditional edges
    workflow.add_conditional_edges("analyze", should_check_availability)
    workflow.add_edge("check_availability", "respond")
    workflow.add_edge("handle_selection", "respond")
    workflow.add_edge("confirm_booking", END)
    workflow.add_edge("respond", END)

    return workflow.compile()


# Create the booking agent
booking_agent = create_booking_workflow()

# Store conversations
conversations: Dict[str, ConversationState] = {}

# Create FastAPI app
app = FastAPI(title="Calendar Booking Agent API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(message: ChatMessage):
    """Main chat endpoint"""
    try:
        # Initialize conversation if not exists
        if message.conversation_id not in conversations:
            conversations[message.conversation_id] = {
                "messages": [],
                "user_intent": "",
                "extracted_info": {},
                "available_slots": [],
                "selected_slot": None,
                "booking_confirmed": False,
                "conversation_phase": "initial",
            }

        # Get current state
        state = conversations[message.conversation_id]

        print(f"DEBUG: Processing message: '{message.message}' in phase: '{state.get('conversation_phase', 'unknown')}'")

        # Add user message to state
        state["messages"].append(HumanMessage(content=message.message))

        # Process through workflow
        result = await asyncio.to_thread(booking_agent.invoke, state)

        # Update conversation state
        conversations[message.conversation_id] = result

        # Get AI response
        ai_response = (
            result["messages"][-1].content
            if result["messages"]
            else "I'm ready to help you book an appointment!"
        )

        # Prepare slots for response (ensure they're JSON serializable)
        response_slots = []
        for slot in result.get("available_slots", []):
            clean_slot = {
                "start": slot["start"],
                "end": slot["end"],
                "formatted": slot["formatted"]
            }
            response_slots.append(clean_slot)

        print(f"DEBUG: Returning response with {len(response_slots)} slots, booking_confirmed: {result.get('booking_confirmed', False)}")

        return ChatResponse(
            response=ai_response,
            available_slots=response_slots,
            booking_confirmed=result.get("booking_confirmed", False),
            conversation_id=message.conversation_id,
        )

    except Exception as e:
        print(f"ERROR in chat endpoint: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "message": "Calendar booking API is running"}


@app.get("/appointments")
async def get_appointments():
    """Get all booked appointments"""
    # Convert datetime objects to ISO format for JSON serialization
    appointments_json = []
    for apt in calendar.appointments:
        apt_copy = apt.copy()
        if isinstance(apt_copy["start"], datetime):
            apt_copy["start"] = apt_copy["start"].isoformat()
        if isinstance(apt_copy["end"], datetime):
            apt_copy["end"] = apt_copy["end"].isoformat()
        appointments_json.append(apt_copy)

    return {"appointments": appointments_json}


@app.delete("/appointments/{appointment_id}")
async def cancel_appointment(appointment_id: str):
    """Cancel an appointment"""
    for i, apt in enumerate(calendar.appointments):
        if apt["id"] == appointment_id:
            removed = calendar.appointments.pop(i)
            return {
                "message": f"Appointment {appointment_id} cancelled",
                "appointment": removed,
            }

    raise HTTPException(status_code=404, detail="Appointment not found")


@app.get("/debug/conversations")
async def debug_conversations():
    """Debug endpoint to see conversation states"""
    debug_data = {}
    for conv_id, state in conversations.items():
        debug_data[conv_id] = {
            "phase": state.get("conversation_phase", "unknown"),
            "intent": state.get("user_intent", ""),
            "available_slots_count": len(state.get("available_slots", [])),
            "has_selected_slot": bool(state.get("selected_slot")),
            "booking_confirmed": state.get("booking_confirmed", False),
            "message_count": len(state.get("messages", []))
        }
    return debug_data


if __name__ == "__main__":
    import uvicorn

    print("Starting Calendar Booking API...")
    print("API will be available at: http://localhost:8000")
    print("Docs available at: http://localhost:8000/docs")
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)