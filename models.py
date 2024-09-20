from pydantic import BaseModel, EmailStr
from typing import List

class Subscriber(BaseModel):
    email: EmailStr
    firstName: str
    lastName: str
    preferences: List[str] = []

class Unsubscriber(BaseModel):
    email: EmailStr
