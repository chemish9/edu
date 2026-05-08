"""Pydantic 요청/응답 모델."""
from pydantic import BaseModel, Field
from typing import Optional


class LoginIn(BaseModel):
	emp_no: str
	password: str


class RegisterIn(BaseModel):
	emp_no: str
	name: str
	password: str
	department: Optional[str] = None
	position: Optional[str] = None
	email: Optional[str] = None


class CaseIn(BaseModel):
	title: str = Field(..., max_length=100)
	summary: str = Field(..., max_length=200)
	content: Optional[str] = ""
	category_id: Optional[int] = None
	ai_tools: list[str] = []
	target_task: Optional[str] = ""
	effect: Optional[str] = ""
	tags: list[str] = []
	status: str = "submitted"  # draft|submitted


class CommentIn(BaseModel):
	content: str = Field(..., min_length=1, max_length=1000)


class CategoryIn(BaseModel):
	name: str
	parent_id: Optional[int] = None


class StatusUpdateIn(BaseModel):
	status: str
	reject_reason: Optional[str] = ""



