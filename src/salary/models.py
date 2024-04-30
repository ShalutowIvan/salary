from sqlalchemy import Integer, String, TIMESTAMP, ForeignKey, Float, Boolean, Text, DateTime, text

from datetime import datetime

from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db import Base

import enum



class State_worker(enum.Enum):
    work = "работает"
    not_work = "уволен"  


class Worker(Base):
	__tablename__ = "worker"
	id: Mapped[int] = mapped_column(primary_key=True)

	speciality:Mapped[str] = mapped_column(String(256))
	current_salary: Mapped[float] = mapped_column(default=0)
	status_work: Mapped[State_worker]

    #связи
	user_id: Mapped[int] = mapped_column(ForeignKey("user.id", ondelete="CASCADE"))
	user: Mapped["User"] = relationship(back_populates="worker")

	salary_increase_date: Mapped["Salary_increase_date"] = relationship(back_populates="worker")



class Salary_increase_date(Base):
	__tablename__ = "salary_increase_date"
	id: Mapped[int] = mapped_column(primary_key=True)
	increase_date: Mapped[datetime] = mapped_column(default=0)
	increase_size: Mapped[float] = mapped_column(default=0)

	#связи
	worker_id: Mapped[int] = mapped_column(ForeignKey("worker.id", ondelete="CASCADE"))
	worker: Mapped["Worker"] = relationship(back_populates="salary_increase_date")

	user_id: Mapped[int] = mapped_column(ForeignKey("user.id", ondelete="CASCADE"))
	user: Mapped["User"] = relationship(back_populates="salary_increase_date")



#когда наступит дата повышения, зп должна увеличиться на тот % который указан в таблице повышения зп









