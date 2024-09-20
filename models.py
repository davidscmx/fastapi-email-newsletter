from pydantic import BaseModel, EmailStr

class Subscriber(BaseModel):
    email: EmailStr
    firstName: str
    lastName: str

class Unsubscriber(BaseModel):
    email: EmailStr
