from fastapi import APIRouter, Depends, HTTPException, Request, Response, Cookie, Form
from sqlalchemy import insert, select, text

from fastapi.responses import HTMLResponse, RedirectResponse

from sqlalchemy import insert, select, text
from sqlalchemy.orm import joinedload

from src.db import get_async_session
from sqlalchemy.ext.asyncio import AsyncSession

from .models import *

from src.regusers.models import User
from src.settings import templates
from src.regusers.secure import test_token_expire, access_token_decode

from jose.exceptions import ExpiredSignatureError

import requests

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



@router_salary.get("/", response_class=HTMLResponse)
async def home(request: Request, Authorization: str | None = Cookie(default=None), RT: str | None = Cookie(default=None), session: AsyncSession = Depends(get_async_session)):

    check = await access_token_decode(acces_token=Authorization)    
    
    flag = False
    if type(check[0]) == ExpiredSignatureError:   
        tokens = await test_token_expire(RT=RT, db=session)        
        check = tokens[2]
        flag = True
    
    context = await base_requisites(db=session, check=check, request=request)
    # good = await session.execute(select(Goods))
    # context["good"] = good.scalars()

    response = templates.TemplateResponse("salary/start.html", context)
    #если флаг True, значит куки истекли и обновились, и их надо обновить у пользователя
    if flag:
        response.set_cookie(key="RT", value=tokens[0])
        response.set_cookie(key="Authorization", value=tokens[1])

    return response



#переделать роутер для просмотра таблицы зарплаты. потом еще сделать роутеры для заполнения зп для суперюзера
@router_showcase.get("/get_salary/", response_class=HTMLResponse)
async def get_salary(request: Request, session: AsyncSession = Depends(get_async_session), Authorization: str | None = Cookie(default=None), RT: str | None = Cookie(default=None)):
    
    check = await access_token_decode(acces_token=Authorization)

    if check[1] == None:#если нет токена то есть пользак вообще не вводил логин пас, то отображаем страницу следующую
        context = await base_requisites(db=session, check=check, request=request)
        return templates.TemplateResponse("salary/if_not_auth.html", context)

    flag = False
    if type(check[0]) == ExpiredSignatureError:   
        tokens = await test_token_expire(RT=RT, db=session)        
        check = tokens[2]
        flag = True
    
    query = select(Salary_increase_date).options(joinedload(Salary_increase_date.worker)).where(Order_list.user_id == int(check[1]))    
    order_list = await session.scalars(query)
    
    kount = await session.scalars(select(Order_counter).where(Order_counter.user_id == int(check[1])))
    #таблица контактов будет постоянно пополняться и со временем станет огромной и жестко тупить при заказах, так как она пополняется от всех пользаков при каждом заказе. надо что-то придумать. 
    
    context = await base_requisites(db=session, check=check, request=request)
    context["order_list"] = order_list.all()
    context["count_order"] = kount.all()

    
    #решить что делать с таблицей контактов и с таблицей заказов, они будут очень сильно разрастаться и тормозить потом

    response = templates.TemplateResponse("showcase/checkout_list.html", context)

    if flag:
        response.set_cookie(key="RT", value=tokens[0])
        response.set_cookie(key="Authorization", value=tokens[1])

    return response




