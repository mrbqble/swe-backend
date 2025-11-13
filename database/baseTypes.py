from pydantic import BaseModel


class IUser(BaseModel):
    id: int

    firstName: str
    lastName: str

    iin: str
    email: str
    phoneNumber: str

    role: str
    password: str


class IProduct(BaseModel):
    id: int

    name: str
    description: str
    price: float
    quantity: int
    user: IUser
