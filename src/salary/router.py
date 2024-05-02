from fastapi import APIRouter, Depends, HTTPException, Request, Response, Cookie, Form
from sqlalchemy import insert, select, text

from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import EmailStr
from sqlalchemy import insert, select, text
from sqlalchemy.orm import joinedload

from src.db import get_async_session
from sqlalchemy.ext.asyncio import AsyncSession

from .models import *

from src.regusers.models import User
from src.settings import templates, KEY5
from src.regusers.secure import test_token_expire, access_token_decode, update_tokens

from jose.exceptions import ExpiredSignatureError

from datetime import datetime, timedelta, date

router_salary = APIRouter(
    prefix="",
    tags=["Salary"]
)



#функция для формирования основного контекста страницы. Можно дополнять ее, чтобы в других функциях удобнее было указывать контекст страницы
async def base_requisites(db, request, check=[False, None, " "]):#db - сессия, check - результат дешифровки аксес токена


    if check[1] != None and check[1] != False:        
        user_name = check[2]
    else:
        user_name = ""

    context = {
    "request": request,    
    "check": check[0],
    "user_name": user_name,
    }

    return context


# главная страница
@router_salary.get("/", response_class=HTMLResponse)
async def home(request: Request, Authorization: str | None = Cookie(default=None), RT: str | None = Cookie(default=None), session: AsyncSession = Depends(get_async_session)):

    check = await access_token_decode(acces_token=Authorization)    
    
    flag = False
    if type(check[0]) == ExpiredSignatureError:   
        tokens = await test_token_expire(RT=RT, db=session)        
        check = tokens[2]
        flag = True
    
    context = await base_requisites(db=session, check=check, request=request)    

    response = templates.TemplateResponse("salary/start.html", context)
    #если флаг True, значит куки истекли и обновились, и их надо обновить у пользователя
    if flag:
        response.set_cookie(key="RT", value=tokens[0])
        response.set_cookie(key="Authorization", value=tokens[1])

    return response


#переделать роутер для просмотра таблицы зарплаты. потом еще сделать роутеры для заполнения зп для суперюзера
@router_salary.get("/get_salary/", response_class=HTMLResponse)
async def get_salary(request: Request, session: AsyncSession = Depends(get_async_session), Authorization: str | None = Cookie(default=None), RT: str | None = Cookie(default=None)):
    
    check = await access_token_decode(acces_token=Authorization)

    if check[1] == None:
        context = await base_requisites(db=session, check=check, request=request)
        return templates.TemplateResponse("salary/if_not_auth.html", context)

    flag = False
    if type(check[0]) == ExpiredSignatureError:   
        tokens = await test_token_expire(RT=RT, db=session)        
        check = tokens[2]
        flag = True
    
    query = select(Salary_increase_date).options(joinedload(Salary_increase_date.worker)).where(Salary_increase_date.user_id == int(check[1]))    
    salary_list = await session.scalars(query)
            
    context = await base_requisites(db=session, check=check, request=request)
    context["salary_list"] = salary_list.all()
    
    response = templates.TemplateResponse("salary/salary_list.html", context)

    if flag:
        response.set_cookie(key="RT", value=tokens[0])
        response.set_cookie(key="Authorization", value=tokens[1])

    return response


#функция get суперюзера
@router_salary.get("/superuser/", response_model=None, response_class=HTMLResponse)
async def become_superuser_get(request: Request, session: AsyncSession = Depends(get_async_session), Authorization: str | None = Cookie(default=None), RT: str | None = Cookie(default=None)):
    
    check = await access_token_decode(acces_token=Authorization)

    flag = False
    if type(check[0]) == ExpiredSignatureError:   
        tokens = await test_token_expire(RT=RT, db=session)        
        check = tokens[2]
        flag = True


    context = await base_requisites(db=session, request=request, check=check)

    user = await session.scalar(select(User).where(User.id == int(check[1])))
        
    if user.is_superuser == True:
        context = await base_requisites(db=session, check=check, request=request)
        return templates.TemplateResponse("salary/you_superuser.html", context)

    response = templates.TemplateResponse("salary/superuser.html", context)

    if flag:
        response.set_cookie(key="RT", value=tokens[0])
        response.set_cookie(key="Authorization", value=tokens[1])

    return response


#функция post суперюзера
@router_salary.post("/superuser/", response_class=HTMLResponse)
async def become_superuser_post(request: Request, session: AsyncSession = Depends(get_async_session), Authorization: str | None = Cookie(default=None), RT: str | None = Cookie(default=None), token: str = Form()):

    check = await access_token_decode(acces_token=Authorization)

    if check[1] == None:
        context = await base_requisites(db=session, check=check, request=request)
        return templates.TemplateResponse("salary/if_not_auth.html", context)

    
    if type(check[0]) == ExpiredSignatureError:   
        tokens = await test_token_expire(RT=RT, db=session)        
        check = tokens[2]

    if token == KEY5:
        user = await session.scalar(select(User).where(User.id == int(check[1])))
        
        if user.is_superuser == True:
            context = await base_requisites(db=session, check=check, request=request)
            return templates.TemplateResponse("salary/you_superuser.html", context)

        user.is_superuser = True
        session.add(user)
        await session.commit()
    else:
        context = await base_requisites(db=session, check=check, request=request)
        return templates.TemplateResponse("salary/if_token_superus_incorrect.html", context)
        
     
    return RedirectResponse("/", status_code=303)


# Ниже роутеры для добавления воркера

#функция get для поиска юзера, весь список берем и напротив каждого юзера будет кнопка для создания воркера
@router_salary.get("/add_worker/search_user/", response_class=HTMLResponse)
async def search_user_get(request: Request, session: AsyncSession = Depends(get_async_session), Authorization: str | None = Cookie(default=None), RT: str | None = Cookie(default=None)):

    check = await access_token_decode(acces_token=Authorization)

    flag = False
    if type(check[0]) == ExpiredSignatureError:   
        tokens = await test_token_expire(RT=RT, db=session)        
        check = tokens[2]
        flag = True

    user = await session.scalar(select(User).where(User.id == int(check[1])))


    if user.is_superuser == False:
        context = await base_requisites(db=session, check=check, request=request)
        return templates.TemplateResponse("salary/you_not_superuser.html", context)
    
    context = await base_requisites(db=session, request=request, check=check)
        
    user_list = await session.scalars(select(User))
    
    context["user_list"] = user_list.all()
        
    response = templates.TemplateResponse("salary/add_worker_search_user.html", context)

    if flag:
        response.set_cookie(key="RT", value=tokens[0])
        response.set_cookie(key="Authorization", value=tokens[1])

    return response



@router_salary.get("/add_worker/create_worker/{email}", response_class=HTMLResponse)
async def create_worker_get(request: Request, email: EmailStr, session: AsyncSession = Depends(get_async_session), Authorization: str | None = Cookie(default=None), RT: str | None = Cookie(default=None) ):

    check = await access_token_decode(acces_token=Authorization)

    flag = False
    if type(check[0]) == ExpiredSignatureError:   
        tokens = await test_token_expire(RT=RT, db=session)        
        check = tokens[2]
        flag = True

    
    user_from_worker = await session.scalar(select(User).where(User.email == email))

    worker = await session.scalar(select(Worker).where(Worker.user_id == user_from_worker.id))
    if worker != None:
        context = await base_requisites(db=session, check=check, request=request)
        return templates.TemplateResponse("salary/worker_is_not_none.html", context)


    context = await base_requisites(db=session, request=request, check=check)    
    context["user"] = user_from_worker
        
    response = templates.TemplateResponse("salary/add_worker_create_worker.html", context)

    if flag:
        response.set_cookie(key="RT", value=tokens[0])
        response.set_cookie(key="Authorization", value=tokens[1])

    return response


@router_salary.post("/add_worker/create_worker/", response_class=HTMLResponse)
async def create_worker_post(request: Request, session: AsyncSession = Depends(get_async_session), Authorization: str | None = Cookie(default=None), RT: str | None = Cookie(default=None), fio: str = Form(), speciality: str = Form(), current_salary: str = Form(), status_work: str = Form(), user_id: int = Form()):

    check = await access_token_decode(acces_token=Authorization)

    flag = False

    if type(check[0]) == ExpiredSignatureError:
        tokens = await test_token_expire(RT=RT, db=session)        
        check = tokens[2]
        flag = True

    worker = Worker(fio=fio, speciality=speciality, current_salary=float(current_salary), status_work=status_work, user_id=user_id)
    session.add(worker)
    await session.commit()
        
    context = await base_requisites(db=session, check=check, request=request)
        
    response = templates.TemplateResponse("salary/start.html", context)

    if flag:        
        response.set_cookie(key="RT", value=tokens[0])
        response.set_cookie(key="Authorization", value=tokens[1])
        
    
    return response



#сделал добавление работников. Нужно теперь еще сделать добавление повышения ЗП для нужного работника. 


#функция для добавления повышения зп воркеру
# @router_salary.get("/get_salary/", response_class=HTMLResponse)
# async def get_salary(request: Request, session: AsyncSession = Depends(get_async_session), Authorization: str | None = Cookie(default=None), RT: str | None = Cookie(default=None)):

#ниже роутера для заполнения повышения ЗП

@router_salary.get("/add_increase_worker/search_worker/", response_class=HTMLResponse)
async def search_worker_get(request: Request, session: AsyncSession = Depends(get_async_session), Authorization: str | None = Cookie(default=None), RT: str | None = Cookie(default=None)):

    check = await access_token_decode(acces_token=Authorization)

    flag = False
    if type(check[0]) == ExpiredSignatureError:   
        tokens = await test_token_expire(RT=RT, db=session)        
        check = tokens[2]
        flag = True

    user = await session.scalar(select(User).where(User.id == int(check[1])))

    if user.is_superuser == False:
        context = await base_requisites(db=session, check=check, request=request)
        return templates.TemplateResponse("salary/you_not_superuser.html", context)
    
    context = await base_requisites(db=session, request=request, check=check)
        
    worker_list = await session.scalars(select(Worker))
    
    context["worker_list"] = worker_list.all()
        
    response = templates.TemplateResponse("salary/add_salary_increase_search_worker.html", context)

    if flag:
        response.set_cookie(key="RT", value=tokens[0])
        response.set_cookie(key="Authorization", value=tokens[1])

    return response



@router_salary.get("/add_increase_worker/create_increase/{id}", response_class=HTMLResponse)
async def create_increase_salary_get(request: Request, id: int, session: AsyncSession = Depends(get_async_session), Authorization: str | None = Cookie(default=None), RT: str | None = Cookie(default=None) ):

    check = await access_token_decode(acces_token=Authorization)

    flag = False
    if type(check[0]) == ExpiredSignatureError:   
        tokens = await test_token_expire(RT=RT, db=session)        
        check = tokens[2]
        flag = True

    
    worker = await session.scalar(select(Worker).where(Worker.id == id))

    salary_increase = await session.scalar(select(Salary_increase_date).where(Salary_increase_date.worker_id == worker.id))
    if salary_increase != None:#проверка, добавляли ли повышение работнику
        context = await base_requisites(db=session, check=check, request=request)
        return templates.TemplateResponse("salary/salary_increase_is_not_none.html", context)


    context = await base_requisites(db=session, request=request, check=check)    
    context["worker"] = worker
        
    response = templates.TemplateResponse("salary/add_salary_increase_create.html", context)

    if flag:
        response.set_cookie(key="RT", value=tokens[0])
        response.set_cookie(key="Authorization", value=tokens[1])

    return response




@router_salary.post("/add_increase_worker/create_increase/", response_class=HTMLResponse)
async def create_increase_salary_post(request: Request, session: AsyncSession = Depends(get_async_session), Authorization: str | None = Cookie(default=None), RT: str | None = Cookie(default=None), increase_date: datetime = Form(), increase_size: float = Form(), worker_id: int = Form(), user_id: int = Form()):

    check = await access_token_decode(acces_token=Authorization)

    flag = False

    if type(check[0]) == ExpiredSignatureError:
        tokens = await test_token_expire(RT=RT, db=session)        
        check = tokens[2]
        flag = True

    increase_salary = Salary_increase_date(increase_date=increase_date, increase_size=increase_size, worker_id=int(worker_id), user_id=user_id)
    session.add(increase_salary)
    await session.commit()
        
    context = await base_requisites(db=session, check=check, request=request)
        
    response = templates.TemplateResponse("salary/start.html", context)

    if flag:        
        response.set_cookie(key="RT", value=tokens[0])
        response.set_cookie(key="Authorization", value=tokens[1])
        
    
    return response