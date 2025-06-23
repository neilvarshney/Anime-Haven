import os
from typing import List, Dict, Optional
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from groq import Groq
import time
from datetime import datetime

# Import our modules
import database
import auth
from auth import get_current_user, get_password_hash, verify_password, create_access_token

load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")

if not GROQ_API_KEY:
    raise ValueError("API key for Groq is missing. Please set the GROQ_API_KEY in the .env file.")

app = FastAPI(title="Anime Recommender Chatbot API", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Groq client
client = Groq(api_key=GROQ_API_KEY)

# Pydantic models
class UserRegister(BaseModel):
    username: str
    email: EmailStr
    password: str

class UserLogin(BaseModel):
    username: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str
    user_id: int
    username: str

class ChatMessage(BaseModel):
    message: str
    conversation_id: Optional[int] = None

class ConversationCreate(BaseModel):
    title: str

class ConversationUpdate(BaseModel):
    title: str

# Initialize database on startup
@app.on_event("startup")
async def startup_event():
    database.initialize_database()

# Authentication endpoints
@app.post("/auth/register", response_model=Dict)
async def register(user_data: UserRegister):
    """Register a new user."""
    # Check if username already exists
    if database.get_user_by_username(user_data.username):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )
    
    # Check if email already exists
    if database.get_user_by_email(user_data.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Hash password and create user
    password_hash = get_password_hash(user_data.password)
    user_id = database.create_user(user_data.username, user_data.email, password_hash)
    
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create user"
        )
    
    return {"message": "User created successfully", "user_id": user_id}

@app.post("/auth/login", response_model=Token)
async def login(user_data: UserLogin):
    """Login user and return JWT token."""
    user = database.get_user_by_username(user_data.username)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password"
        )
    
    if not verify_password(user_data.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password"
        )
    
    # Create access token
    access_token = create_access_token(data={"sub": str(user["id"]), "username": user["username"]})
    
    return Token(
        access_token=access_token,
        token_type="bearer",
        user_id=user["id"],
        username=user["username"]
    )

@app.get("/auth/me")
async def get_current_user_info(current_user_id: int = Depends(get_current_user)):
    """Get current user information."""
    user = database.get_user_by_id(current_user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return user

# Conversation management endpoints
@app.get("/conversations")
async def get_conversations(current_user_id: int = Depends(get_current_user)):
    """Get all conversations for the current user."""
    conversations = database.get_user_conversations(current_user_id)
    return {"conversations": conversations}

@app.post("/conversations")
async def create_conversation(
    conversation_data: ConversationCreate,
    current_user_id: int = Depends(get_current_user)
):
    """Create a new conversation."""
    conversation_id = database.create_conversation(current_user_id, conversation_data.title)
    if not conversation_id:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create conversation"
        )
    
    return {"conversation_id": conversation_id, "title": conversation_data.title}

@app.get("/conversations/{conversation_id}")
async def get_conversation(
    conversation_id: int,
    current_user_id: int = Depends(get_current_user)
):
    """Get a specific conversation with all its messages."""
    conversation = database.get_conversation_with_messages(conversation_id, current_user_id)
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found"
        )
    return conversation

@app.put("/conversations/{conversation_id}")
async def update_conversation(
    conversation_id: int,
    conversation_data: ConversationUpdate,
    current_user_id: int = Depends(get_current_user)
):
    """Update conversation title."""
    success = database.update_conversation_title(conversation_id, current_user_id, conversation_data.title)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found"
        )
    return {"message": "Conversation updated successfully"}

@app.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: int,
    current_user_id: int = Depends(get_current_user)
):
    """Delete a conversation and all its messages."""
    success = database.delete_conversation(conversation_id, current_user_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found"
        )
    return {"message": "Conversation deleted successfully"}

# Chat functionality
def query_groq_api(messages: List[Dict[str, str]]) -> str:
    """Make a request to the Groq API."""
    try:
        start_time = time.time()
        
        completion = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=messages,
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

@app.post("/chat")
async def chat(
    chat_data: ChatMessage,
    current_user_id: int = Depends(get_current_user)
):
    """Send a message and get AI response."""
    conversation_id = chat_data.conversation_id
    
    # If no conversation_id provided, create a new conversation
    if not conversation_id:
        # Create a new conversation with a default title
        title = f"Chat {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        conversation_id = database.create_conversation(current_user_id, title)
        if not conversation_id:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create conversation"
            )
    else:
        # Verify the conversation belongs to the user
        conversation = database.get_conversation_by_id(conversation_id, current_user_id)
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found"
            )
    
    # Get existing messages for this conversation
    existing_messages = database.get_conversation_messages(conversation_id)
    
    # Prepare messages for Groq API (include system message)
    api_messages = [
        {"role": "system", "content": "You are a Anime Expert and will help the user find the best anime for them. Be enthusiastic about anime and provide detailed recommendations with explanations."}
    ]
    
    # Add existing messages
    for msg in existing_messages:
        api_messages.append({"role": msg["role"], "content": msg["content"]})
    
    # Add the new user message
    api_messages.append({"role": "user", "content": chat_data.message})
    
    # Get AI response
    ai_response = query_groq_api(api_messages)
    
    # Save both messages to database
    database.add_message(conversation_id, "user", chat_data.message)
    database.add_message(conversation_id, "assistant", ai_response)
    
    return {
        "response": ai_response,
        "conversation_id": conversation_id
    }

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)