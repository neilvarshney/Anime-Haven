import os
from typing import List, Dict
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from groq import Groq
import history
from history import *
from fastapi.middleware.cors import CORSMiddleware
import datetime
import time



load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")


if not GROQ_API_KEY:
    raise ValueError("API key for Groq is missing. Please set the GROQ_API_KEY in the .env file.")


app = FastAPI()


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


client = Groq(api_key=GROQ_API_KEY)


class UserInput(BaseModel):
    message: str
    role: str = "user"
    conversation_id: str


# Conversation class to store the conversation history using a dictionary.
class Conversation:
    def __init__(self):
        self.messages: List[Dict[str, str]] = [
            {"role": "system", "content": "You are a Anime Expert and will help the user find the best anime for them."}
        ]
        self.active: bool = True

conversations: Dict[str, Conversation] = {}



# Makes a request to the Groq API. Expects a Conversation object as input so that it can use the conversation history.
# Returns a string of the response from the API.
def query_groq_api(conversation: Conversation) -> str:
    try:
        start_time = time.time()
        
        completion = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=conversation.messages,
            temperature=1,
            max_tokens=1024,
            top_p=1,
            stream=True,
            stop=None,
        )
        
        response = ""
        for chunk in completion:
            response += chunk.choices[0].delta.content or ""
        
        end_time = time.time()
        response_time = end_time - start_time
        print(f"API Response Time: {response_time:.2f} seconds")
        
        return response
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error with Groq API: {str(e)}")


def get_or_create_conversation(conversation_id: str) -> Conversation:
    if conversation_id not in conversations:
        conversations[conversation_id] = Conversation()
    return conversations[conversation_id]

def history_db_Setup():
    initialize_database()

@app.get("/users/{user_id}")
async def history(user_id: int):
    user_data = history.get_user_by_id(user_id)
    if user_data:
        print(user_data)
        return user_data
    else: 
        raise HTTPException(status_code=404, detail=f"User with ID {user_id} not found")




@app.post("/chat/")
async def chat(input: UserInput):
    conversation = get_or_create_conversation(input.conversation_id)

    if not conversation.active:
        raise HTTPException(
            status_code=400, 
            detail="The chat session has ended. Please start a new session."
        )
        
    try:
        # Append the user's message to the conversation
        conversation.messages.append({
            "role": input.role,
            "content": input.message
        })
        
        response = query_groq_api(conversation)
        
        conversation.messages.append({
            "role": "assistant",
            "content": response
        })
        
        return {
            "response": response,
            "conversation_id": input.conversation_id
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
if __name__ == "__main__":
    import uvicorn
    history_db_Setup()
    add_user("hi")
    userJSON = get_user_by_id(1)
    print(userJSON)
    uvicorn.run(app, host="0.0.0.0", port=8000)