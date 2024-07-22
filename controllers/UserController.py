from fastapi import HTTPException, Depends, Header, Response
from fastapi.security import OAuth2PasswordRequestForm
from models.User import User
from fastapi_utils.cbv import cbv
from fastapi_utils.inferring_router import InferringRouter
from services.UserService import UserService

router_user = InferringRouter()

@cbv(router_user)
class UserController:
    def __init__(self):
        self.userService = UserService()

    @router_user.post('/register')
    def register(self, user: User):
        try: 
            if '@' not in user.username:
                raise HTTPException(status_code=400, detail="Invalid username: username should be your e-mail")
            usr = self.userService.register(user)
            if usr is not False:
                return Response(content= f"User registered successfully!" ,status_code=200)
            else:
                raise HTTPException(status_code=422, detail="User already exists")
                
        except Exception as e:
            raise HTTPException(status_code=e.status_code, detail=str(e.detail))
            
    @router_user.post('/token')
    def get_access_token(self, form_data: OAuth2PasswordRequestForm = Depends()):
        try:
            access_token = self.userService.get_access_token(form_data)
            if access_token['access_token'] is None:
                raise HTTPException(status_code=400, detail="Incorrect username or password")
            return Response(content=f"{access_token}" ,status_code=200)
        except Exception as e:
            raise HTTPException(status_code=e.status_code, detail=str(e.detail))
            
    @router_user.post('/logout')
    def logout(self, token: str = Header(None)):
        try:
            if token is None:
                raise HTTPException(status_code=401, detail="Invalid token!")
            self.userService.logout(token)
            return Response(content="Logged out successfully!", status_code=200)
        except Exception as e:
            raise HTTPException(status_code=e.status_code, detail=str(e.detail))