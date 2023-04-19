from typing import Union, List
from typing_extensions import Annotated
from pydantic import BaseModel
from fastapi import FastAPI, HTTPException, File, UploadFile, Form
from fastapi.responses import FileResponse
import json
import datetime
import jwt
import face_recognition
from PIL import Image
import numpy as np
import re
import io 
import base64


def get_from_base64(codec):
    base64_data = re.sub('^data:image/.+;base64,' ,  "" , codec)
    byte_data = base64.b64decode(base64_data)
    image_data = io.BytesIO(byte_data)
    with Image.open(image_data) as img:
        img = img.convert('RGB')
    return np.array(img)

SECRET = "REKSTI2023"

app = FastAPI()
# uvicorn main:app --reload --host 0.0.0.0 --port 80

@app.get("/")
def test_root():
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
    work_history: List[WorkHistory]


class EmployeeData(BaseModel):
    email: str
    id: int
    name: str
    position: str

@app.get("/user/{user_id}/photo")
def get_photo(user_id: int):
    with open("data.json", "r") as f:
        data = json.loads(f.read())
        employees:list[Employee] = data['employees']
    for employee in employees:
        if employee['id'] == user_id:
            return FileResponse(employee['email'] + ".jpg")

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
                    "token": encoded_jwt,
                    "user": employee
                }
    raise HTTPException(401, "wrong email or password")



class PresenceParams(BaseModel):
    image: str
    token: str

@app.post("/presence")
async def presence(params: PresenceParams):
    token = params.token
    image = params.image
    try:
        user: EmployeeData = jwt.decode(token, SECRET, ["HS256"])
    except jwt.DecodeError as e:
        raise HTTPException(400, "Invalid token: " + str(e))
    
    with open("data.json", "r") as f:
        data = json.loads(f.read())
        employees: list[Employee] = data["employees"]
    
    user_valid = False
    user = None
    for employee in employees:
        if employee['email'] == user['email'] and employee['id'] == user['id']:
            user_valid = True
            user = employee
    
    if not user_valid:
        raise HTTPException(401, "Invalid user")
    
    face = face_recognition.load_image_file(user.email + ".jpg")
    try:
        face = face_recognition.face_encodings(face)[0]
        compare = face_recognition.face_encodings(get_from_base64(image))[0]
        known_faces = [face]
        result = face_recognition.compare_faces(known_faces, compare)
        print(result)
    except IndexError:
        print("no faces")

    return {"hello": "world"}


@app.get("/user/{user_id}/history")
def get_history(user_id: int):
    with open("data.json", "r") as f:
        data = json.loads(f.read())
        employees:list[Employee] = data['employees']
    for employee in employees:
        if employee['id'] == user_id:
            return {
                "data": employee['work_history']
            }