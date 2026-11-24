from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, StringConstraints, model_validator


ShortText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=140)]
TeamName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=70)]
Institution = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]


class LoginInput(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class SignupInput(LoginInput):
    pass


class ResendVerificationInput(BaseModel):
    email: EmailStr


class RegisterMember(BaseModel):
    full_name: ShortText
    email: EmailStr
    student_id: ShortText


class TeamRegistration(BaseModel):
    name: TeamName
    college: Institution
    members: list[RegisterMember] = Field(min_length=4, max_length=6)

    @model_validator(mode="after")
    def validate_members(self):
        addresses = [member.email.lower() for member in self.members]
        if len(addresses) != len(set(addresses)):
            raise ValueError("Each team member must have a different email address.")
        return self


class ReviewInput(BaseModel):
    math_rigor: int = Field(ge=0, le=20)
    originality: int = Field(ge=0, le=20)
    impact: int = Field(ge=0, le=20)
    feasibility: int = Field(ge=0, le=20)
    presentation: int = Field(ge=0, le=20)
    notes: str = Field(default="", max_length=5000)

    @property
    def total_score(self) -> int:
        return self.math_rigor + self.originality + self.impact + self.feasibility + self.presentation


class ShortlistInput(BaseModel):
    selected: bool


class PaymentReviewInput(BaseModel):
    status: Literal["verified", "rejected"]
    note: str = Field(default="", max_length=1000)


class PaymentReferenceInput(BaseModel):
    payment_reference: str = Field(min_length=3, max_length=200)
