from fastapi import Form, APIRouter, Depends, Request, Cookie
from fastapi.responses import HTMLResponse, RedirectResponse

from sqlalchemy import insert, select, text
from pydantic import EmailStr

from src.db import get_async_session
from sqlalchemy.ext.asyncio import AsyncSession
from src.settings import templates, EXPIRE_TIME, KEY, KEY2, ALG, EXPIRE_TIME_REFRESH, KEY3, KEY4

from .models import *
from src.salary.models import *
from src.salary.router import base_requisites

# from .schemas import *

from .secure import pwd_context, create_access_token, create_refresh_token, update_tokens, send_email_verify, send_email_restore_password

# from jose import jwt
import jwt

from datetime import datetime, timedelta

from jose.exceptions import ExpiredSignatureError


router_reg = APIRouter(
    prefix="/regusers",
    tags=["Regusers"]
)


#метод get для страницы регистрации
@router_reg.get("/registration")
async def registration_get(request: Request, session: AsyncSession = Depends(get_async_session)):
    
    context = await base_requisites(db=session, request=request)

    response = templates.TemplateResponse("regusers/register.html", context)
    return response


#метод post для страницы регистрации
@router_reg.post("/registration", response_model=None, status_code=201)
async def registration_post(request: Request, session: AsyncSession = Depends(get_async_session), name: str = Form(), email: str = Form(), password1: str = Form(), password2: str = Form()):
    
    #тут проверки пароля    
    if password1 != password2:
        context = await base_requisites(db=session, request=request)
        context["password_mismatch"] = "Пароли не совпадают!"
        response = templates.TemplateResponse("regusers/register.html", context)
        return response

    if len(password1) < 8 or password1.lower() == password1 or password1.upper() == password1 or not any(i.isdigit() for i in password1) or all(i.isdigit() for i in password1):
        context = await base_requisites(db=session, request=request)
        context["password_not_strong"] = "Пароль должен быть не менее 8 символов и должен содержать заглавные, строчные буквы и цифры!"
        response = templates.TemplateResponse("regusers/register.html", context)
        return response

    user = User(name=name, email=email, hashed_password=pwd_context.hash(password1))
    
    session.add(user)
    await session.commit() 

    await send_email_verify(user=user)

    return RedirectResponse("/regusers/verification/check/", status_code=303)


#это подсказка, о том что нужно зайти на почту и перейти по ссылке для активации пользователя
@router_reg.get("/verification/check/", response_model=None, status_code=201)
async def confirm_email(request: Request, session: AsyncSession = Depends(get_async_session)):

    t = "Перейдите в вашу почту и перейдите по ссылке из письма для подтверждения адреса почты и активации пользователя"
    
    context = await base_requisites(db=session, request=request)
    context["t"] = t

    response = templates.TemplateResponse("regusers/check_email.html", context)
    return response


#функция обработки ссылки из письма при активации пользователя
@router_reg.get("/verification/check_user/{token}", response_model=None, status_code=201)
async def activate_user(request: Request, token: str, session: AsyncSession = Depends(get_async_session)):    
    try:
        payload = jwt.decode(token, KEY3, algorithms=[ALG])
        
        user_id = payload.get("sub")
        if user_id is None:
            context = await base_requisites(db=session, request=request)
            return templates.TemplateResponse("regusers/user_not_found.html", context)
            
    
    except Exception as ex:
        context = await base_requisites(db=session, request=request)
        return templates.TemplateResponse("regusers/user_not_found.html", context)
    

    user = await session.scalar(select(User).where(User.id == int(user_id)))   
    
    user.is_active = True
    session.add(user)
    await session.commit()
    
    return RedirectResponse("/regusers/auth/", status_code=303) 


#функция get для страницы забыли пароль
@router_reg.get("/forgot_password/", response_model=None, response_class=HTMLResponse)
async def forgot_password_get(request: Request, session: AsyncSession = Depends(get_async_session)):
    
    context = await base_requisites(db=session, request=request)

    response = templates.TemplateResponse("regusers/forgot_password.html", context)
    return response


#функция post для страницы забыли пароль
@router_reg.post("/forgot_password/", response_model=None, response_class=HTMLResponse)
async def forgot_password_post(request: Request, session: AsyncSession = Depends(get_async_session), email: EmailStr = Form()):
    user = await session.scalar(select(User).where(User.email == email))

    if user is None:
        context = await base_requisites(db=session, request=request)
        context["user_not_found"] = "Пользователь не найден!"
        response = templates.TemplateResponse("regusers/forgot_password.html", context)
        return response

    #отправляем пользователю на почту ссылку для восстановления пароля
    await send_email_restore_password(user=user)

    return RedirectResponse("/regusers/restore/pass/", status_code=303)


#это подсказка, о том что нужно зайти на почту и перейти по ссылке при сбросе пароля
@router_reg.get("/restore/pass/", response_model=None, status_code=201)
async def confirm_email_restore_pass(request: Request, session: AsyncSession = Depends(get_async_session)):

    t = "Перейдите в вашу почту и перейдите по ссылке из письма для восстановления пароля пользователя"
    
    context = await base_requisites(db=session, request=request)
    context["t"] = t
    response = templates.TemplateResponse("regusers/go_to_restore_password.html", context)
    return response


#get запрос для отрисовки страницы формы восстановления пароля
@router_reg.get("/restore/password_user/{token}")
async def restore_password_user_get(request: Request, token: str, session: AsyncSession = Depends(get_async_session)):
    
    context = await base_requisites(db=session, request=request)
    context["token"] = token

    response = templates.TemplateResponse("regusers/new_password.html", context)
    return response


#функция для обработки ссылки из письма для сброса пароля. token автоматом указыватся в форме, и поле с токеном в html сделал невидимым
@router_reg.post("/restore/password_user/")
async def restore_password_user(request: Request, session: AsyncSession = Depends(get_async_session), password1: str = Form(), password2: str = Form(), token: str = Form()):
    try:
        payload = jwt.decode(token, KEY4, algorithms=[ALG])
        user_id = payload.get("sub")
        if user_id is None:
            context = await base_requisites(db=session, request=request)
            context["user_not_found"] = "Пользователь не найден! Перейдите по ссылке из письма повторно и повторите попытку ввода нового пароля!"
            response = templates.TemplateResponse("regusers/new_password.html", context)            
            return response

    except Exception as ex:
        context = await base_requisites(db=session, request=request)
        context["url_incorrect"] = "Некорректная ссылка! Перейдите по ссылке из письма повторно и повторите попытку ввода нового пароля!"
        response = templates.TemplateResponse("regusers/new_password.html", context)        
        return response

    if password1 != password2:
        context = await base_requisites(db=session, request=request)
        context["password_mismatch"] = "Пароли не совпадают! Перейдите по ссылке из письма повторно и повторите попытку ввода нового пароля!"
        response = templates.TemplateResponse("regusers/new_password.html", context)
        
        return response

    if len(password1) < 8 or password1.lower() == password1 or password1.upper() == password1 or not any(i.isdigit() for i in password1) or all(i.isdigit() for i in password1):
        context = await base_requisites(db=session, request=request)
        context["password_not_strong"] = "Пароль должен быть не менее 8 символов и должен содержать заглавные, строчные буквы и цифры! Перейдите по ссылке из письма повторно и повторите попытку ввода нового пароля!"
        response = templates.TemplateResponse("regusers/new_password.html", context)
        
        return response

    user = await session.scalar(select(User).where(User.id == int(user_id)))
    user.hashed_password = pwd_context.hash(password1)
    session.add(user)
    await session.commit()
    return RedirectResponse("/regusers/auth/", status_code=303)


#функция get авторизации
@router_reg.get("/auth", response_model=None, response_class=HTMLResponse)
async def auth_get(request: Request, session: AsyncSession = Depends(get_async_session)):
    
    context = await base_requisites(db=session, request=request)

    response = templates.TemplateResponse("regusers/login.html", context)
    return response


#функция post авторизации
@router_reg.post("/auth", response_model=None, response_class=HTMLResponse)
async def auth_user(request: Request, session: AsyncSession = Depends(get_async_session), email: EmailStr = Form(), password: str = Form()):

    user: User = await session.scalar(select(User).where(User.email == email))#ищем пользователя по емейл
    
    if not user:
        context = await base_requisites(db=session, request=request)
        context["user_not_found"] = "Пользователь не зарегистрирован!"
        response = templates.TemplateResponse("regusers/login.html", context)
        return response
    
    if not pwd_context.verify(password, user.hashed_password):#сверка пароля с БД
        context = await base_requisites(db=session, request=request)
        context["password_incorrect"] = "Неверный пароль!"
        response = templates.TemplateResponse("regusers/login.html", context)
        return response
        
    if user.is_active != True:
        context = await base_requisites(db=session, request=request)
        context["user_not_active"] = "Пользователь не активирован! Перейдите по ссылке из письма, которое пришло вам на почту для активации!"
        response = templates.TemplateResponse("regusers/login.html", context)
        return response

    
    refresh_token: Token = await session.scalar(select(Token).where(Token.user_id == user.id))
    
    #тут проверка истек ли рефреш токен
    try:
        payload = jwt.decode(refresh_token.refresh_token, KEY2, algorithms=[ALG])        

    except Exception as ex:#если истек рефреш то его просто удаляем, и нужно заново логиниться
        print("РЕФРЕШ ТОКЕН ИСТЕК")
        print(ex)
        if type(ex) == ExpiredSignatureError:            
            await session.delete(refresh_token)
            await session.commit()
            refresh_token = None

    #Теперь если рефреш токена нет или он истек, то создаем токены
    if not refresh_token:
        #рефреш токен
        refresh_token_expires = timedelta(minutes=int(EXPIRE_TIME_REFRESH))        
        refresh_token_jwt = create_refresh_token(data={"sub": str(user.id)}, expires_delta=refresh_token_expires)

        #аксес токен
        access_token_expires = timedelta(minutes=int(EXPIRE_TIME))        
        access_token_jwt = create_access_token(data={"sub": str(user.id), "user_name": user.name}, expires_delta=access_token_expires)
        
        #создаем объект токена и добавляем его в базу
        token: Token = Token(user_id=user.id, refresh_token=refresh_token_jwt)
        session.add(token)       
        await session.commit()
        await session.refresh(token)
        refresh_token: Token = await session.scalar(select(Token).where(Token.user_id == user.id))#перезаписываем в переменную объект рефреш токена, так как нужен именно объект нового токена
    else:#иначе если рефреш токен не истек, то обновляем access токен
        access_token_expires = timedelta(minutes=int(EXPIRE_TIME))
        access_token_jwt = create_access_token(data={"sub": str(user.id), "user_name": user.name}, expires_delta=access_token_expires)
    
    
    context = await base_requisites(db=session, request=request)
    context["user_name"] = user.name
    context["check"] = True#это для проверки на фронте
        
    #теперь передаем контекст и куки с токенами пользователю и переходим на главную страницу
    response = templates.TemplateResponse("salary/start.html", context)    
    response.set_cookie(key="RT", value=refresh_token.refresh_token)
    response.set_cookie(key="Authorization", value=access_token_jwt)
   
    return response
    

#выход пользователя
@router_reg.get("/logout")
async def logout_user(request: Request, Authorization: str | None = Cookie(default=None), RT: str | None = Cookie(default=None), session: AsyncSession = Depends(get_async_session)):
    
    context = await base_requisites(db=session, request=request)

    response = templates.TemplateResponse("regusers/login.html", context)
    
    if RT != None:
        us_token: Token = await session.scalar(select(Token).where(Token.refresh_token == RT))
        if us_token:
            await session.delete(us_token)
            await session.commit()
        response.delete_cookie("RT")
        response.delete_cookie("Authorization")

    return response