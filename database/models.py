from sqlalchemy import Column, ForeignKey, Integer, String
from server.database.database import Base


class UserModel(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)

    firstName = Column(String, index=True)
    lastName = Column(String, index=True)

    iin = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    phoneNumber = Column(String, unique=True, index=True)

    role = Column(String)
    password = Column(String)


class ProductModel(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)

    name = Column(String)
    description = Column(String)
    price = Column(Integer)
    quantity = Column(Integer)
    user = Column(Integer, ForeignKey("users.id"))
