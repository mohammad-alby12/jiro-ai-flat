from pydantic import BaseModel, Field

class ConversationCreate(BaseModel):
    title: str = Field(default="New chat", max_length=180)

class ConversationRename(BaseModel):
    title: str = Field(min_length=1, max_length=180)

class ChatRequest(BaseModel):
    conversation_id: str
    message: str = Field(min_length=1, max_length=20000)
    system_prompt: str = Field(default="You are JIRO AI, a helpful, honest assistant.", max_length=4000)
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    top_p: float = Field(default=0.9, gt=0.0, le=1.0)
    max_new_tokens: int = Field(default=384, ge=1, le=2048)
