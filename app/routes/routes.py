from fastapi import APIRouter
from random import randint
from app.services.openai_service import OpenAIService, FirebaseOrganizer

router = APIRouter()

@router.get("/input_message")
def input_message(message_received: str, session_id: str = None):
    if not session_id:
        session_id = f"visitor_{randint(0, 10000)}"

    o = OpenAIService()
    f = FirebaseOrganizer()

    response = o.send_message(
        session_id,
        {"role": "user", "content": message_received}
    )

    # f.save_message(session_id, message_received, response)
    return {"session_id": session_id, "response": response}


@router.get("/get_messages")
def get_messages(session_id: str):
    f = FirebaseOrganizer()
    messages = f.get_messages(session_id) 
    return {"messages": messages}