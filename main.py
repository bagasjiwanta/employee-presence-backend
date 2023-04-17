from typing import Union
from pydantic import BaseModel
from fastapi import FastAPI, HTTPException
import json
import datetime
import jwt

SECRET = "REKSTI2023"

app = FastAPI()


@app.get("/")
def read_root():
    return {"Hello": "World"}


class LoginParams(BaseModel):
    email: str
    password: str


class WorkHistory(BaseModel):
    clock_in: datetime.datetime
    clock_out: datetime.datetime


class Employee(BaseModel):
    email: str
    password: str
    id: int
    name: str
    position: str
    work_history: list[WorkHistory]


@app.post("/login")
def login(login_params: LoginParams):
    with open("data.json", "r") as f:
        data = json.loads(f.read())
        employees:list[Employee] = data['employees']

    
    for employee in employees:
        if employee['email'] == login_params.email:
            if employee['password'] == login_params.password:
                employee.pop("password")
                employee.pop("work_history")
                encoded_jwt = jwt.encode(employee, SECRET)
                return {
                    "token": encoded_jwt
                }
    raise HTTPException(401, "wrong email or password")



@app.get("/items/{item_id}")
def read_item(item_id: int, q: Union[str, None] = None):
    return {"item_id": item_id, "q": q}