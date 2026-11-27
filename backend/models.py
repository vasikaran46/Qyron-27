from typing import Annotated, Literal, Optional
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
    members: list[RegisterMember] = Field(min_length=2, max_length=4)

    @model_validator(mode="after")
    def validate_members(self):
        addresses = [member.email.lower() for member in self.members]
        if len(addresses) != len(set(addresses)):
            raise ValueError("Each team member must have a different email address.")
        return self


class ReviewInput(BaseModel):
    problem_understanding: int = Field(default=0, ge=0, le=15, description="Problem understanding and relevance (15%)")
    quantum_implementation: int = Field(default=0, ge=0, le=25, description="Quantum computing implementation (25%)")
    originality: int = Field(default=0, ge=0, le=20, description="Innovation and originality (20%)")
    technical_execution: int = Field(default=0, ge=0, le=20, description="Technical execution and working prototype (20%)")
    impact_scalability: int = Field(default=0, ge=0, le=10, description="Practical impact and scalability (10%)")
    presentation: int = Field(default=0, ge=0, le=10, description="Presentation and demonstration (10%)")
    notes: str = Field(default="", max_length=5000)

    # Legacy field fallbacks for backwards compatibility
    math_rigor: Optional[int] = Field(default=None, ge=0, le=25)
    impact: Optional[int] = Field(default=None, ge=0, le=20)
    feasibility: Optional[int] = Field(default=None, ge=0, le=20)

    @property
    def total_score(self) -> int:
        if (
            self.problem_understanding
            or self.quantum_implementation
            or self.technical_execution
            or self.impact_scalability
        ):
            return (
                self.problem_understanding
                + self.quantum_implementation
                + self.originality
                + self.technical_execution
                + self.impact_scalability
                + self.presentation
            )
        # Legacy fallback
        legacy_sum = (
            (self.math_rigor or 0)
            + (self.originality or 0)
            + (self.impact or 0)
            + (self.feasibility or 0)
            + (self.presentation or 0)
        )
        return legacy_sum


class ShortlistInput(BaseModel):
    selected: bool


class PaymentReviewInput(BaseModel):
    status: Literal["verified", "rejected"]
    note: str = Field(default="", max_length=1000)


class PaymentReferenceInput(BaseModel):
    payment_reference: str = Field(min_length=3, max_length=200)
