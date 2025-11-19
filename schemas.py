"""
Database Schemas

Define your MongoDB collection schemas here using Pydantic models.
These schemas are used for data validation in your application.

Each Pydantic model represents a collection in your database.
Model name is converted to lowercase for the collection name:
- User -> "user" collection
- Product -> "product" collection
- BlogPost -> "blogs" collection
"""

from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List
from datetime import date as DateType

# Example schemas (replace with your own):

class User(BaseModel):
    """
    Users collection schema
    Collection name: "user" (lowercase of class name)
    """
    name: str = Field(..., description="Full name")
    email: EmailStr = Field(..., description="Email address")
    address: str = Field(..., description="Address")
    age: Optional[int] = Field(None, ge=0, le=120, description="Age in years")
    is_active: bool = Field(True, description="Whether user is active")

class Product(BaseModel):
    """
    Products collection schema
    Collection name: "product" (lowercase of class name)
    """
    title: str = Field(..., description="Product title")
    description: Optional[str] = Field(None, description="Product description")
    price: float = Field(..., ge=0, description="Price in dollars")
    category: str = Field(..., description="Product category")
    in_stock: bool = Field(True, description="Whether product is in stock")

# --------------------------------------------------
# Bookkeeping SaaS Schemas
# --------------------------------------------------

class InvoiceLine(BaseModel):
    description: str
    quantity: float = Field(1, ge=0)
    unit_price: float = Field(..., ge=0)
    total: Optional[float] = None

class Invoice(BaseModel):
    """
    Invoices collection schema
    Collection name: "invoice"
    """
    invoice_number: str = Field(..., description="Invoice ID/number")
    vendor_name: str = Field(..., description="Vendor name")
    vendor_email: Optional[EmailStr] = None
    invoice_date: DateType = Field(..., description="Invoice date")
    due_date: Optional[DateType] = None
    currency: str = Field("USD", min_length=3, max_length=3)
    subtotal: Optional[float] = Field(None, ge=0)
    tax: Optional[float] = Field(0, ge=0)
    total: float = Field(..., ge=0)
    lines: Optional[List[InvoiceLine]] = None

class BankTransaction(BaseModel):
    """
    Bank transactions collection schema
    Collection name: "banktransaction"
    """
    bank_ref: Optional[str] = Field(None, description="Bank reference or memo")
    description: str = Field(..., description="Transaction description")
    date: DateType = Field(..., description="Transaction date")
    amount: float = Field(..., description="Positive=credit, Negative=debit")
    currency: str = Field("USD", min_length=3, max_length=3)

class Match(BaseModel):
    """
    Matches between invoices and bank transactions
    Collection name: "match"
    """
    invoice_number: str
    bank_transaction_id: str
    confidence: float = Field(..., ge=0, le=1)
    reason: Optional[str] = None
