from sqlalchemy import select
from .models import User, Token

from passlib.context import CryptContext
# from jose import jwt
import jwt
from src.settings import KEY, KEY2, KEY3, KEY4, ALG, EXPIRE_TIME, EXPIRE_TIME_REFRESH
from datetime import datetime, timedelta
from jose.exceptions import ExpiredSignatureError

#импорты для отправки почты
from src.settings import PORT, HOST, HOST_USER, HOST_PASSWORD
import smtplib
from email.message import EmailMessage


#переменная для хеширования пароля
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


#метод для создания access токена
def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta    
    else:
        expire = datetime.utcnow() + timedelta(minutes=int(EXPIRE_TIME))
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, KEY, algorithm=ALG)
    return encoded_jwt


#метод для создания refresh токена
def create_refresh_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta    
    else:
        expire = datetime.utcnow() + timedelta(minutes=int(EXPIRE_TIME_REFRESH))
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, KEY2, algorithm=ALG)
    return encoded_jwt


#метод для обновления токенов
async def update_tokens(RT, db):
	#расшифровка рефреш токена
	try:
		payload = jwt.decode(RT, KEY2, algorithms=[ALG])
		pl_id = payload.get("sub")		
		print("Токен расшифрован успешно")
	except Exception as ex:
		print("Ошибка расшифровки Refresh токена ниже")
		print(ex)
		if type(ex) == ExpiredSignatureError:
			us_token: Token = await db.scalar(select(Token).where(Token.refresh_token == RT))
			if us_token:
				await db.delete(us_token)
				await db.commit()
		
		return [False, False]#возвращаю 2 раза False, чтобы не проходили проверки на фронте

    #создаем новый рефреш и аксес. Данные для создания токенов берем из декодированного токена из пейлоада
        
    #проверка совпадает ли токен из кук с базой - для безопасности, в случае если злоумышленник обновил уже токен, а мы нет, то все токены должны удалиться
	RT_in_db: Token = await db.scalar(select(Token).where(Token.refresh_token == RT))#ищем рефреш в ДБ по токену из кук	
	
	if not RT_in_db:
		tk: Token = await db.scalar(select(Token).where(Token.user_id == int(pl_id)))#ищем токен по ID пользователя и удаляем его, это чтобы мошенников обезвредить и у них не было доступа. А пользователь сможет ввести свои логин и пароль заново. 
		if tk:
			await db.delete(tk)
			await db.commit()
			
		print("Токен не совпадает с базой, теперь токены удалены.")
		return [False, False]

	#если токен совпал с базой, то мы обновляем оба токена
	#рефреш токен
	refresh_token_expires = timedelta(minutes=int(EXPIRE_TIME_REFRESH))    
	refresh_token_jwt = create_refresh_token(data={"sub": str(pl_id)}, expires_delta=refresh_token_expires)

	#аксес токен
	user: User = await db.scalar(select(User).where(User.id == int(pl_id)))
	access_token_expires = timedelta(minutes=int(EXPIRE_TIME))
	access_token_jwt = create_access_token(data={"sub": pl_id, "user_name": user.name}, expires_delta=access_token_expires)

	#обновляем рефреш в базе	
	new_RT: Token = Token(user_id=int(pl_id), refresh_token=refresh_token_jwt)#для создания объекта рефреш токена нужен Ид пользователя

	await db.delete(RT_in_db)
	db.add(new_RT)
	await db.commit()
	await db.refresh(new_RT)

	return [refresh_token_jwt, access_token_jwt]


#функция проверки токена из куки
async def access_token_decode(acces_token):    
    try:
        payload = jwt.decode(acces_token, KEY, algorithms=[ALG])        
        user_id = payload.get("sub")
        user_name = payload.get("user_name")
        if user_id is None:
            print("Нет такого пользователя")
            return [False, None, " "]
                
    except Exception as ex:
                
        if type(ex) == ExpiredSignatureError:#если время действия токена истекло, то вывод принта.
            
            print("Ошибка истечения Access токена тут")
            print(ex)
            return [ex, None, " "]
    
        return [False, None, " "]#если токена нет вообще, то это возвращается, это нужно для того чтобы не было доступа у пользователя
        
    return [True, user_id, user_name]#3 параметра возвращаем, потому что они нужны для формирования контекста основной страницы


#метод для подтверждения регистрации пользователя.
async def send_email_verify(user, use_https=False):
	email = EmailMessage()
	email['Subject'] = 'Подтверждение регистрации в интернет магазине'
	email['From'] = HOST_USER
	email['To'] = user.email

	http = "http" if use_https == False else "https"	 

	token = jwt.encode({"sub": str(user.id)}, KEY3, algorithm=ALG)
		
	email.set_content(f"<a href={http}://127.0.0.1:8000/regusers/verification/check_user/{token}><h1>ССЫЛКА</h1></a>" , subtype='html')
    
	with smtplib.SMTP_SSL(HOST, PORT) as server:
		server.login(HOST_USER, HOST_PASSWORD)
		server.send_message(email)

    

#функция для удобной проверки и обновления токенов
async def test_token_expire(RT, db):
    tokens = await update_tokens(RT=RT, db=db)
    check = await access_token_decode(acces_token=tokens[1])
    return (tokens[0], tokens[1], check)#рефреш, аксес, дешифровка аксес


    
#метод для восстановления забытого пароля пользователя. используется другой ключ в отличии от метода активации
async def send_email_restore_password(user, use_https=False):
	email = EmailMessage()
	email['Subject'] = 'Восстановление пароля'
	email['From'] = HOST_USER
	email['To'] = user.email

	http = "http" if use_https == False else "https"	 

	token = jwt.encode({"sub": str(user.id)}, KEY4, algorithm=ALG)
		
	email.set_content(f"<a href={http}://127.0.0.1:8000/regusers/restore/password_user/{token}><h1>ССЫЛКА</h1></a>" , subtype='html')
    
	with smtplib.SMTP_SSL(HOST, PORT) as server:
		server.login(HOST_USER, HOST_PASSWORD)
		server.send_message(email)


   
   


