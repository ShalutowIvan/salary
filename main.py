from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from src.regusers.router import router_reg
from src.salary.router import router_salary


app = FastAPI(title="Просмотр зарплаты", debug=True)
app.mount("/static", StaticFiles(directory="src/static"), name="static")
app.include_router(router_salary)
app.include_router(router_reg)


if __name__ == "__main__":
    uvicorn.run("main:app", port=8000, host="127.0.0.1", reload=True)