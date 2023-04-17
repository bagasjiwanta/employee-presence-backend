from typing import Union, Annotated
from pydantic import BaseModel
from fastapi import FastAPI, HTTPException, File, UploadFile, Form
import json
import datetime
import jwt
import face_recognition

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


class EmployeeData(BaseModel):
    email: str
    id: int
    name: str
    position: str


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


@app.post("/presence")
async def presence(
    file: Annotated[UploadFile, File()],
    token: Annotated[str, Form()]
):
    try:
        user: EmployeeData = jwt.decode(token, SECRET, ["HS256"])
    except jwt.DecodeError as e:
        raise HTTPException(400, "Invalid token: " + str(e))
    
    with open("data.json", "r") as f:
        data = json.loads(f.read())
        employees: list[Employee] = data["employees"]
    
    user_valid = False
    for employee in employees:
        if employee['email'] == user['email'] and employee['id'] == user['id']:
            user_valid = True
    
    if not user_valid:
        raise HTTPException(401, "Invalid user")
    
    if file.filename.split(".")[-1] not in ["JPG", "jpg", "JPEG", "jpeg", "png", "PNG"]:
        raise HTTPException(400, "Invalid image format")

    
    
    biden_image = face_recognition.load_image_file("portrait.jpg")
    test_face = face_recognition.load_image_file("test.jpg")
    test_face2 = face_recognition.load_image_file("test2.jpg")
    try:
        biden_face_encoding = face_recognition.face_encodings(biden_image)[0]
        test_face_encoding = face_recognition.face_encodings(test_face)[0]
        test_face2_encoding = face_recognition.face_encodings(test_face2)[0]
    except IndexError:
        print("no faces")
    
    known_faces = [
        biden_face_encoding
    ]

    results = face_recognition.compare_faces(known_faces, test_face_encoding)
    results2 = face_recognition.compare_faces(known_faces, test_face2_encoding)
    print(results, results2)

    return {"hello": "world"}


@app.get("/items/{item_id}")
def read_item(item_id: int, q: Union[str, None] = None):
    return {"item_id": item_id, "q": q}