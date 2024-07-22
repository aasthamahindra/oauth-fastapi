# implementation of IUserRepository class
from repositories.IUserRespository import IUserRepository
from entity_manager.entity_manager import entity_manager
from models.User import User, ActiveSession
import os
from dotenv import load_dotenv
from fastapi.security import OAuth2PasswordRequestForm
from fastapi import Depends, HTTPException
from passlib.context import CryptContext
from datetime import timedelta, datetime
from passlib.hash import bcrypt
import jwt
from jwt import PyJWTError

dotenv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
load_dotenv(dotenv_path)

# CryptContext for hashing passwords
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class UserRepository(IUserRepository):
    def __init__(self):
        self.em = entity_manager.get_collection(os.environ.get("USER_COLLECTION"))
        self.activeSessionEntityManager = entity_manager.get_collection(os.environ.get("ACTIVE_SESSIONS_COLLECTION"))

    # signup a user if it doesn't exist in db
    def register(self, user: User):
        usr = self.em.find_one({"username": user.username })

        # use bcrypt to encrypt passwords
        if usr is None:
            self.em.insert_one({
                "username": user.username,
                "password": bcrypt.using(rounds=12).hash(user.password)
            })
            return user
        else:
            return False
        
    # generate JWT token
    def create_access_token(self, data: dict, expires_delta):
        to_encode = data.copy()
        expire = datetime.now() + expires_delta
        to_encode.update({ "exp": expire })
        encoded_jwt = jwt.encode(to_encode, key=os.environ.get("SECRET"), algorithm='HS256')
        return encoded_jwt
    
    def get_access_token(self, form_data: OAuth2PasswordRequestForm = Depends()):        
        access_token_expires = timedelta(hours=12)
        access_token = self.create_access_token(
            data={"sub": form_data.username}, expires_delta=access_token_expires
        )
        return access_token
    
    def get_user(self, username: str):
        usr = self.em.find_one({ "username": username })

        if usr is not None:
            return User(
                username = usr["username"],
                password = usr["password"]
            )
        return None
    
    # check if given password is correct or not
    def is_password_correct(self, form_data: OAuth2PasswordRequestForm = Depends()) -> bool:
        user = self.get_user(form_data.username)

        if user is None or not pwd_context.verify(form_data.password, user.password):
            return False
        return True
    
    def authenticate(self, token: str):
        try:
            payload = jwt.decode(token, key=os.environ.get("SECRET"), algorithms=['HS256'])
            username: str = payload.get("sub")
            if username is None:
                raise HTTPException(status_code=400, detail="Could not validate credentials, user not found.")
            
            # check if the token has expired
            expiry_time = payload.get("exp")
            if expiry_time is None or expiry_time < datetime.now().timestamp():
                self.activeSessionEntityManager.delete_many({
                    "username": username
                })
                raise HTTPException(status_code=401, detail="Authentication failed, invalid or expired token.")
            
            #check if the username exists in the active sessions
            session = self.activeSessionEntityManager.find_one({
                    "username": username
                })
            if not session:
                raise HTTPException(status_code=401, detail="User session not found.")
            
        except PyJWTError:
            raise HTTPException(status_code=401, detail="Authentication failed, invalid or expired token.")
        
    def register_token_in_session(self, token: str):
        try:
            payload = jwt.decode(token, key=os.environ.get("SECRET"), algorithms='HS256')
            print(payload)
            user, expiration_time = payload.get("sub"), payload.get("exp")
            expiration_datetime = datetime.fromtimestamp(expiration_time)

            new_active_session = ActiveSession(
                username=user,
                access_token=token,
                expiry_time=expiration_datetime
            )

            self.activeSessionEntityManager.insert_one(new_active_session.model_dump())
        except:
            raise HTTPException(status_code=401, detail="Authentication failed, invalid or expired token.")
        
    def logout(self, token: str):
        self.activeSessionEntityManager.delete_many({
            "access_token": token
        })

    def is_session_active(self, username: str):
        # check if user has an active session
        existing_session = self.activeSessionEntityManager.find_one({
            "username": username
        })
        if not existing_session: return False

        # if active session exits, check if token is still valid
        try:
            payload = jwt.decode(existing_session["access_token"], key=os.environ.get("SECRET"), algorithms=['HS256'])
            expiry_time = payload.get("exp")
            current_time = datetime.now().timestamp()

            if expiry_time is None or expiry_time < current_time:
                # token has expired
                self.activeSessionEntityManager.delete_many({
                    "username": username
                })
                return False
        
        except PyJWTError:
            # there was an error in processing the token, delete session and return false
            self.activeSessionEntityManager.delete_many({
                    "username": username
                })
            return False
        return True
    
    def get_access_token_from_active_session(self, username: str):
        existing_session = self.activeSessionEntityManager.find_one({ "username": username})
        if existing_session is not None:
            return existing_session["access_token"]
        return None
