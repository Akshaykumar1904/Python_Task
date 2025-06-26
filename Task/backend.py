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
            if 9 <= current.hour < 17:
                slot_end = current + timedelta(hours=1)
                conflict = False
                for apt in self.appointments:
                    if current < apt["end"] and slot_end > apt["start"]:
                        conflict = True
                        break
                if not conflict:
                    available_slots.append(
                        {
                            "start": current,
                            "end": slot_end,
                            "formatted": current.strftime("%A, %B %d at %I:%M %p"),
                        }
                    )
            current += timedelta(hours=1)

        return available_slots[:10]

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


class ChatMessage(BaseModel):
    message: str
    available_slots: List[Dict] = []
    booking_confirmed: bool = False
    conversation_id: str


class ChatResponse(BaseModel):
    message: str
    available_slots: List[Dict] = []
    booking_confirmed: bool = False
    conversation_id: str


def extract_date_time_info(text: str) -> Dict[str, Any]:
    info = {}
    date_patterns = [
        r"tomorrow",
        r"next week",
        r"monday",
        r"tuesday",
        r"wednesday",
        r"thursday",
        r"friday",
        r"saturday",
        r"sunday",
    ]
    time_patterns = [
        r"(\d{1,2})\s*(am|pm)",
        r"(\d{1,2}):(\d{2})\s*(am|pm)",
        r"morning",
        r"afternoon",
        r"evening",
    ]
    text_lower = text.lower()

    for pattern in date_patterns:
        if re.search(pattern, text_lower):
            info["date_preference"] = pattern
            break

    for pattern in time_patterns:
        match = re.search(pattern, text_lower)
        if match:
            info["time_preference"] = match.group()
            break

    purpose_keywords = ["meeting", "consultation", "call", "interview", "demo"]
    for keyword in purpose_keywords:
        if keyword in text_lower:
            info["purpose"] = keyword
            break

    return info


def determine_intent(text: str) -> str:
    text_lower = text.lower()
    if any(
        word in text_lower for word in ["book", "schedule", "appointment", "meeting"]
    ):
        return "book_appointment"
    elif any(word in text_lower for word in ["available", "free", "slots", "times"]):
        return "check_availability"
    elif any(
        word in text_lower for word in ["confirm", "yes", "that works", "sounds good"]
    ):
        return "confirm_booking"
    elif any(word in text_lower for word in ["cancel", "change", "reschedule"]):
        return "modify_booking"
    else:
        return "general_inquiry"


def get_date_range_from_preference(preference: str) -> tuple:
    now = datetime.now()
    if "tomorrow" in preference:
        start = now.replace(hour=9, minute=0, second=0, microsecond=0) + timedelta(
            days=1
        )
        end = start + timedelta(hours=8)
    elif "next week" in preference:
        days_ahead = 7 - now.weekday()
        start = now.replace(hour=9, minute=0, second=0, microsecond=0) + timedelta(
            days=days_ahead
        )
        end = start + timedelta(days=5, hours=8)
    else:
        start = now.replace(hour=9, minute=0, second=0, microsecond=0) + timedelta(
            days=1
        )
        end = start + timedelta(days=3, hours=8)
    return start, end


def analyze_input(state: ConversationState) -> ConversationState:
    last_message = state["messages"][-1].content
    intent = determine_intent(last_message)
    extracted_info = extract_date_time_info(last_message)
    state["user_intent"] = intent
    state["extracted_info"] = {**state.get("extracted_info", {}), **extracted_info}
    return state


def check_availablity(state: ConversationState) -> ConversationState:
    extracted_info = state["extracted_info"]
    if "date_preference" in extracted_info:
        start_date, end_date = get_date_range_from_preference(
            extracted_info["date_preference"]
        )
    else:
        now = datetime.now()
        start_date = now.replace(hour=9, minute=0, second=0, microsecond=0) + timedelta(
            days=1
        )
        end_date = start_date + timedelta(days=3, hours=8)
    available_slots = calendar.get_availability(start_date, end_date)
    state["available_slots"] = available_slots
    return state


def generate_response(state: ConversationState) -> ConversationState:
    intent = state["user_intent"]
    available_slots = state.get("available_slots", [])
    extracted_info = state.get("extracted_info", {})

    if intent == "book_appointment":
        if available_slots:
            response = "I found some available time for you:\n\n"
            for i, slot in enumerate(available_slots, 1):
                response += f"{i}. {slot['formatted']}\n"
            response += "\nWhich slot would you prefer? Let me know the number and your preference!"
        else:
            response = "I'm looking for available time slots. Could you tell me your preferred date and time?"
    elif intent == "check_availability":
        if available_slots:
            response = "Here are the available time slots:\n\n"
            for i, slot in enumerate(available_slots, 1):
                response += f"{i}. {slot['formatted']}\n"
            response += "\nWould you like to book any of these slots?"
        else:
            response = "Let me check availability for you. What date and time would you prefer?"
    else:
        response = "I'm here to help with bookings. How can I assist you?"

    state["messages"].append(AIMessage(content=response))
    return state


def handler_slot_selection(state: ConversationState) -> ConversationState:
    """handle user's slot selection"""
    last_message = state["messages"][-1].content.lower()
    available_slots = state.get("available_slots", [])

    for i in range(1, min(11, len(available_slots) + 1)):
        if str(i) in last_message:
            state["selected_slot"] = available_slots[i - 1]
            state["user_intent"] = "confirm_booking"
            break

    return state


def create_booking_workflow():
    workflow = StateGraph(ConversationState)

    # add nodes
    workflow.add_node("analyze", analyze_input)
    workflow.add_node("check_availablity", check_availablity)
    workflow.add_node("handle_selection", handler_slot_selection)
    workflow.add_node("respond", generate_response)

    workflow.set_entry_point("analyze")

    def should_check_availblity(state):
        intent = state["user_intent"]
        return (
            "check_availablity"
            if intent in ["book_appointment", "check_availability"]
            else "handle_selection"
        )

    def should_handle_selection(state):
        intent = state["user_intent"]
        available_slots = state.get("available_slots", [])
        return (
            "handle_selection"
            if intent == "general_inquiry" and available_slots
            else "respond"
        )

    workflow.add_conditional_edges("analyze", should_check_availblity)
    workflow.add_edge("check_availablity", "respond")
    workflow.add_conditional_edges("handle_selection", should_handle_selection)
    workflow.add_edge("respond", END)

    return workflow.compile()


booking_agent = create_booking_workflow()

conversations: Dict[str, ConversationState] = {}

app = FastAPI(title="Calendar Booking App Agent")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/chat", response_model=ChatResponse)
async def chat_endPoint(message: ChatMessage):
    """Main chat endpoint"""
    try:
        if message.conversation_id not in conversations:
            conversations[message.conversation_id] = {
                "messages": [],
                "user_intent": "",
                "extracted_info": {},
                "available_slots": [],
                "selected_slot": None,
                "booking_confirmed": False,
            }

        state = conversations[message.conversation_id]
        state["messages"].append(HumanMessage(content=message.message))

        result = await asyncio.to_thread(booking_agent.invoke, state)

        conversations[message.conversation_id] = result

        ai_response = result["messages"][-1].content

        return ChatResponse(
            response=ai_response,
            available_slots=result.get("available_slots", []),
            booking_confirmed=result.get("booking_confirmed", False),
            conversation_id=message.conversation_id,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


@app.get("/appointments")
async def get_appointments():
    """Get all booked appointments"""
    return {"appointments": calendar.appointments}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
