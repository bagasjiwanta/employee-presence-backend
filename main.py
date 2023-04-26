from typing import Union, List
from typing_extensions import Annotated
from pydantic import BaseModel
from fastapi import FastAPI, HTTPException, File, UploadFile, Form, Depends
from fastapi.responses import FileResponse
from fastapi.security import OAuth2PasswordBearer
import json
import datetime
import jwt
import face_recognition
from PIL import Image
import hashlib
from dotenv import load_dotenv
import os
import PIL.Image as Image
from fastapi import Request, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials


class BearerToken(HTTPBearer):
    def __init__(self, auto_error: bool = True):
        super(BearerToken, self).__init__(auto_error=auto_error)

    async def __call__(self, request: Request):
        credentials: HTTPAuthorizationCredentials = await super(BearerToken, self).__call__(request)
        if credentials:
            if not credentials.scheme == "Bearer":
                raise HTTPException(
                    status_code=403, detail="Invalid authentication scheme.")
            if not self.verify_jwt(credentials.credentials):
                raise HTTPException(
                    status_code=403, detail="Invalid token or expired token.")
            return credentials.credentials
        else:
            raise HTTPException(
                status_code=403, detail="Invalid authorization code.")

    def verify_jwt(self, jwtoken: str) -> bool:
        isTokenValid: bool = False

        try:
            payload = jwt.decode(jwtoken, SECRET, ["HS256"])
        except:
            payload = None
        if payload:
            isTokenValid = True
        return isTokenValid


load_dotenv()

SECRET = os.getenv("SECRET")

app = FastAPI()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


class LoginParams(BaseModel):
    email: str
    password: str


class WorkHistory(BaseModel):
    clock_in: str
    clock_out: str


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


class SignupResponse(BaseModel):
    message: str
    token: str


@app.post("/signup")
def signup(
    image: Annotated[UploadFile, File()],
    email: Annotated[str, Form()],
    password: Annotated[str, Form()],
    position: Annotated[str, Form()],
    name: Annotated[str, Form()]
) -> SignupResponse:
    with open("data/employees.json", "r") as f:
        employees = json.loads(f.read())

    largest_id = employees[0]['id']
    for employee in employees:
        if employee['email'] == email:
            raise HTTPException(409, "user already exist")
        if employee['id'] >= largest_id:
            largest_id = employee['id']

    employee: Employee = {
        "email": email,
        "password": hashlib.sha256(password.encode()).hexdigest(),
        "id": largest_id + 1,
        "name": name,
        "position": position,
        "work_history": []
    }
    face = face_recognition.load_image_file(image.file)
    try:
        face = face_recognition.face_encodings(face)[0]
    except IndexError:
        raise HTTPException(400, "face not recognized")

    employees.append(employee)

    with open("data/employees.json", "w") as f:
        f.write(json.dumps(employees, indent=2))

    # with open("data/images/" + email + ".jpg", "wb") as f:
    #     f.write(image)
    del employee['work_history']
    del employee['password']
    save = Image.open(image.file)
    # save = save.rotate(180)
    save.save("data/images/" + email + ".jpg")

    return {
        "message": "user created",
        "token": jwt.encode(employee, SECRET)
    }


class LoginResponse(BaseModel):
    token: str
    user: EmployeeData


@app.post("/login")
def login(login_params: LoginParams) -> LoginResponse:
    with open("data/employees.json", "r") as f:
        employees: list[Employee] = json.loads(f.read())

    for employee in employees:
        if employee['email'] == login_params.email:
            if employee['password'] == hashlib.sha256(login_params.password.encode()).hexdigest():
                employee.pop("password")
                employee.pop("work_history")
                encoded_jwt = jwt.encode(employee, SECRET)
                return {
                    "message": "login success",
                    "data": {
                        "token": encoded_jwt,
                        "user": employee
                    }
                }
    raise HTTPException(401, "wrong email or password")


class PresenceResponse(BaseModel):
    message: str


@app.post("/user/presence")
async def presence(
    image: Annotated[UploadFile, File()],
    token: Annotated[str, Depends(BearerToken())],
    local_time: Annotated[str, Form()]
) -> PresenceResponse:
    try:
        user: EmployeeData = jwt.decode(token, SECRET, ["HS256"])
    except jwt.DecodeError as employee:
        raise HTTPException(400, "Invalid token: " + str(employee))

    with open("data/employees.json", "r") as f:
        employees: list[Employee] = json.loads(f.read())

    user_valid = False
    employee: Employee = None
    for em in employees:
        if em['email'] == user['email'] and em['id'] == user['id']:
            user_valid = True
            user = em
            employee = em

    if not user_valid:
        raise HTTPException(401, "Invalid user")

    loc = "data/images/" + user['email'] + ".jpg"
    face = face_recognition.load_image_file(loc)
    image = face_recognition.load_image_file(image.file)
    try:
        face = face_recognition.face_encodings(face)[0]
        compare = face_recognition.face_encodings(image)[0]
        known_faces = [face]
        result = face_recognition.compare_faces(known_faces, compare)
        if not result[0]:
            raise HTTPException(400, "face does not match")

        most_recent = employee['work_history'][-1]
        if 'clock_out' in most_recent:
            most_recent_date = datetime.datetime.fromisoformat(
                most_recent['clock_out'])
        else:
            most_recent_date = datetime.datetime.fromisoformat(
                most_recent['clock_in'])
        presence_date = datetime.datetime.fromisoformat(local_time)
        if most_recent_date.date() < presence_date.date():
            employee['work_history'].append({
                "clock_in": presence_date.isoformat()
            })
        else:
            if "clock_out" in most_recent:
                raise HTTPException(
                    409, "cannot add more attendance for today")
            else:
                most_recent['clock_out'] = presence_date.isoformat()

        with open("data/employees.json", "r+") as f:
            f.write(json.dumps(employees, indent=2))

        return {
            "message": "success"
        }

    except IndexError:
        raise HTTPException(500)


@app.get("/user/photo", response_class=FileResponse)
def get_photo(token: Annotated[str, Depends(BearerToken())]) -> FileResponse:
    user: EmployeeData = None
    try:
        user: EmployeeData = jwt.decode(token, SECRET, ["HS256"])
    except jwt.DecodeError as e:
        raise HTTPException(400, "Invalid token: " + str(e))

    with open("data/employees.json", "r") as f:
        employees: list[Employee] = json.loads(f.read())
    for employee in employees:
        if employee['id'] == user['id']:
            return FileResponse("data/images/" + employee['email'] + ".jpg")
    raise HTTPException(500)


class GetHistoryResponse(BaseModel):
    data: List[WorkHistory]


@app.get("/user/history")
def get_history(token: Annotated[str, Depends(BearerToken())]) -> GetHistoryResponse:
    user: EmployeeData = None
    try:
        user: EmployeeData = jwt.decode(token, SECRET, ["HS256"])
    except jwt.DecodeError as e:
        raise HTTPException(400, "Invalid token: " + str(e))

    with open("data/employees.json", "r") as f:
        employees: list[Employee] = json.loads(f.read())

    for employee in employees:
        if employee['id'] == user['id']:
            return {
                "data": employee['work_history']
            }

    raise HTTPException(404, "history not found")

# sudo su
# source env/bin/activate
# python3 -m uvicorn main:app --host 0.0.0.0 --port 80 --reload
