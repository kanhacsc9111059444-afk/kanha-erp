from __future__ import annotations

from datetime import date, datetime
from typing import Any, Optional

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )


class Company(Base, TimestampMixin):
    __tablename__ = "companies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(200))
    gstin: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    currency: Mapped[str] = mapped_column(String(8), default="INR")
    locale: Mapped[str] = mapped_column(String(16), default="en")
    modules_enabled: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    settings_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class Branch(Base, TimestampMixin):
    __tablename__ = "branches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    code: Mapped[str] = mapped_column(String(32))
    name: Mapped[str] = mapped_column(String(200))
    city: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class Warehouse(Base, TimestampMixin):
    __tablename__ = "warehouses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    branch_id: Mapped[Optional[int]] = mapped_column(ForeignKey("branches.id"), nullable=True)
    code: Mapped[str] = mapped_column(String(32))
    name: Mapped[str] = mapped_column(String(200))
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class Role(Base, TimestampMixin):
    __tablename__ = "roles"
    __table_args__ = (UniqueConstraint("company_id", "code"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    code: Mapped[str] = mapped_column(String(64))
    name: Mapped[str] = mapped_column(String(120))
    permissions: Mapped[list[Any]] = mapped_column(JSON, default=list)


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    branch_id: Mapped[Optional[int]] = mapped_column(ForeignKey("branches.id"), nullable=True)
    email: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(200))
    password_hash: Mapped[str] = mapped_column(String(255))
    role_id: Mapped[Optional[int]] = mapped_column(ForeignKey("roles.id"), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_superadmin: Mapped[bool] = mapped_column(Boolean, default=False)
    theme: Mapped[str] = mapped_column(String(32), default="light")
    ui_prefs: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    # Bump to invalidate ALL JWTs (stolen phone / force logout everywhere)
    session_epoch: Mapped[int] = mapped_column(Integer, default=0)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[Optional[int]] = mapped_column(Integer, index=True, nullable=True)
    user_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    action: Mapped[str] = mapped_column(String(64))
    entity: Mapped[str] = mapped_column(String(64))
    entity_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    detail: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class CustomField(Base, TimestampMixin):
    __tablename__ = "custom_fields"
    __table_args__ = (UniqueConstraint("company_id", "entity", "field_key"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    entity: Mapped[str] = mapped_column(String(64))  # lead, customer, product, invoice...
    field_key: Mapped[str] = mapped_column(String(64))
    label: Mapped[str] = mapped_column(String(120))
    field_type: Mapped[str] = mapped_column(String(32), default="text")
    required: Mapped[bool] = mapped_column(Boolean, default=False)
    options: Mapped[list[Any]] = mapped_column(JSON, default=list)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)


class Workflow(Base, TimestampMixin):
    __tablename__ = "workflows"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    entity: Mapped[str] = mapped_column(String(64))
    steps: Mapped[list[Any]] = mapped_column(JSON, default=list)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int] = mapped_column(Integer, index=True)
    user_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    title: Mapped[str] = mapped_column(String(200))
    body: Mapped[str] = mapped_column(Text, default="")
    read: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


# ??? CRM ?????????????????????????????????????????????????????????????????????


class Lead(Base, TimestampMixin):
    __tablename__ = "leads"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    company_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    source: Mapped[str] = mapped_column(String(64), default="web")
    stage: Mapped[str] = mapped_column(String(64), default="new")  # new/qualified/won/lost
    value: Mapped[float] = mapped_column(Float, default=0)
    owner_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    custom: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    notes: Mapped[str] = mapped_column(Text, default="")


class Customer(Base, TimestampMixin):
    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    code: Mapped[str] = mapped_column(String(32))
    name: Mapped[str] = mapped_column(String(200))
    email: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    gstin: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    billing_address: Mapped[str] = mapped_column(Text, default="")
    custom: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    # Channel / dealer fields
    party_type: Mapped[str] = mapped_column(String(32), default="customer")  # customer/dealer/distributor
    is_dealer: Mapped[bool] = mapped_column(Boolean, default=False)
    credit_limit: Mapped[float] = mapped_column(Float, default=0)
    price_list_code: Mapped[str] = mapped_column(String(64), default="STANDARD")
    region: Mapped[str] = mapped_column(String(100), default="")


class Opportunity(Base, TimestampMixin):
    __tablename__ = "opportunities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    lead_id: Mapped[Optional[int]] = mapped_column(ForeignKey("leads.id"), nullable=True)
    customer_id: Mapped[Optional[int]] = mapped_column(ForeignKey("customers.id"), nullable=True)
    title: Mapped[str] = mapped_column(String(200))
    stage: Mapped[str] = mapped_column(String(64), default="prospect")
    amount: Mapped[float] = mapped_column(Float, default=0)
    probability: Mapped[int] = mapped_column(Integer, default=20)
    close_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)


class Quotation(Base, TimestampMixin):
    __tablename__ = "quotations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    number: Mapped[str] = mapped_column(String(40))
    customer_id: Mapped[Optional[int]] = mapped_column(ForeignKey("customers.id"), nullable=True)
    lead_id: Mapped[Optional[int]] = mapped_column(ForeignKey("leads.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="draft")
    subtotal: Mapped[float] = mapped_column(Float, default=0)
    tax: Mapped[float] = mapped_column(Float, default=0)
    total: Mapped[float] = mapped_column(Float, default=0)
    lines: Mapped[list[Any]] = mapped_column(JSON, default=list)
    valid_until: Mapped[Optional[date]] = mapped_column(Date, nullable=True)


# ??? Inventory / Catalog ?????????????????????????????????????????????????????


class Product(Base, TimestampMixin):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    sku: Mapped[str] = mapped_column(String(64))
    name: Mapped[str] = mapped_column(String(200))
    category: Mapped[str] = mapped_column(String(100), default="General")
    brand: Mapped[str] = mapped_column(String(100), default="")
    uom: Mapped[str] = mapped_column(String(16), default="NOS")
    sale_price: Mapped[float] = mapped_column(Float, default=0)
    cost_price: Mapped[float] = mapped_column(Float, default=0)
    gst_rate: Mapped[float] = mapped_column(Float, default=18)
    track_serial: Mapped[bool] = mapped_column(Boolean, default=False)
    track_batch: Mapped[bool] = mapped_column(Boolean, default=False)
    barcode: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    custom: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class StockBalance(Base, TimestampMixin):
    __tablename__ = "stock_balances"
    __table_args__ = (UniqueConstraint("company_id", "warehouse_id", "product_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    warehouse_id: Mapped[int] = mapped_column(ForeignKey("warehouses.id"))
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))
    qty: Mapped[float] = mapped_column(Float, default=0)
    avg_cost: Mapped[float] = mapped_column(Float, default=0)


class StockMove(Base, TimestampMixin):
    __tablename__ = "stock_moves"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))
    warehouse_id: Mapped[int] = mapped_column(ForeignKey("warehouses.id"))
    qty: Mapped[float] = mapped_column(Float)  # +in / -out
    move_type: Mapped[str] = mapped_column(String(32))  # receipt/issue/transfer/adjust
    ref: Mapped[str] = mapped_column(String(64), default="")
    notes: Mapped[str] = mapped_column(Text, default="")
    batch_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # FEFO link


class MaterialIssue(Base, TimestampMixin):
    """Store Material Issue voucher (SBAC Issue Items)."""

    __tablename__ = "material_issues"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    number: Mapped[str] = mapped_column(String(40))
    warehouse_id: Mapped[Optional[int]] = mapped_column(ForeignKey("warehouses.id"), nullable=True)
    indent_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    department: Mapped[str] = mapped_column(String(100), default="")
    purpose: Mapped[str] = mapped_column(String(200), default="")
    status: Mapped[str] = mapped_column(String(32), default="posted")
    lines: Mapped[list[Any]] = mapped_column(JSON, default=list)
    custom: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


class StoreReceive(Base, TimestampMixin):
    """Internal Material Receive / return to store (not purchase MRN)."""

    __tablename__ = "store_receives"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    number: Mapped[str] = mapped_column(String(40))
    warehouse_id: Mapped[Optional[int]] = mapped_column(ForeignKey("warehouses.id"), nullable=True)
    source: Mapped[str] = mapped_column(String(100), default="return")  # return/production/other
    status: Mapped[str] = mapped_column(String(32), default="posted")
    lines: Mapped[list[Any]] = mapped_column(JSON, default=list)
    custom: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


class PhysicalStock(Base, TimestampMixin):
    """Physical stock count sheet — draft → approved applies variance adjusts."""

    __tablename__ = "physical_stocks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    number: Mapped[str] = mapped_column(String(40))
    warehouse_id: Mapped[Optional[int]] = mapped_column(ForeignKey("warehouses.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="draft")  # draft/approved
    lines: Mapped[list[Any]] = mapped_column(JSON, default=list)
    notes: Mapped[str] = mapped_column(Text, default="")
    custom: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


class GodownTransfer(Base, TimestampMixin):
    """Multi-line godown transfer note."""

    __tablename__ = "godown_transfers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    number: Mapped[str] = mapped_column(String(40))
    from_warehouse_id: Mapped[int] = mapped_column(ForeignKey("warehouses.id"))
    to_warehouse_id: Mapped[int] = mapped_column(ForeignKey("warehouses.id"))
    status: Mapped[str] = mapped_column(String(32), default="posted")
    lines: Mapped[list[Any]] = mapped_column(JSON, default=list)
    notes: Mapped[str] = mapped_column(Text, default="")
    custom: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


# ??? Sales ???????????????????????????????????????????????????????????????????


class SalesOrder(Base, TimestampMixin):
    __tablename__ = "sales_orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    number: Mapped[str] = mapped_column(String(40))
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"))
    quotation_id: Mapped[Optional[int]] = mapped_column(ForeignKey("quotations.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="draft")
    approval_status: Mapped[str] = mapped_column(String(32), default="none")
    subtotal: Mapped[float] = mapped_column(Float, default=0)
    tax: Mapped[float] = mapped_column(Float, default=0)
    total: Mapped[float] = mapped_column(Float, default=0)
    lines: Mapped[list[Any]] = mapped_column(JSON, default=list)
    warehouse_id: Mapped[Optional[int]] = mapped_column(ForeignKey("warehouses.id"), nullable=True)
    # SBAC header extras (remarks, transport, addresses, dates…)
    custom: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


class Delivery(Base, TimestampMixin):
    __tablename__ = "deliveries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    number: Mapped[str] = mapped_column(String(40))
    sales_order_id: Mapped[Optional[int]] = mapped_column(ForeignKey("sales_orders.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="draft")
    lines: Mapped[list[Any]] = mapped_column(JSON, default=list)
    invoice_id: Mapped[Optional[int]] = mapped_column(ForeignKey("invoices.id"), nullable=True)
    custom: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


class Invoice(Base, TimestampMixin):
    __tablename__ = "invoices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    number: Mapped[str] = mapped_column(String(40))
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"))
    sales_order_id: Mapped[Optional[int]] = mapped_column(ForeignKey("sales_orders.id"), nullable=True)
    invoice_type: Mapped[str] = mapped_column(String(32), default="sales")  # sales/credit/debit
    status: Mapped[str] = mapped_column(String(32), default="draft")
    invoice_date: Mapped[date] = mapped_column(Date, default=date.today)
    due_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    subtotal: Mapped[float] = mapped_column(Float, default=0)
    tax: Mapped[float] = mapped_column(Float, default=0)
    total: Mapped[float] = mapped_column(Float, default=0)
    paid: Mapped[float] = mapped_column(Float, default=0)
    lines: Mapped[list[Any]] = mapped_column(JSON, default=list)
    recurring: Mapped[bool] = mapped_column(Boolean, default=False)
    custom: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


class Payment(Base, TimestampMixin):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    invoice_id: Mapped[Optional[int]] = mapped_column(ForeignKey("invoices.id"), nullable=True)
    party_type: Mapped[str] = mapped_column(String(32), default="customer")
    party_id: Mapped[int] = mapped_column(Integer)
    amount: Mapped[float] = mapped_column(Float)
    method: Mapped[str] = mapped_column(String(32), default="bank")
    reference: Mapped[str] = mapped_column(String(100), default="")
    payment_date: Mapped[date] = mapped_column(Date, default=date.today)
    gateway: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)  # razorpay/stripe
    # Bill-by-bill: [{invoice_id|purchase_invoice_id, amount}] — CA-grade outstanding
    allocations: Mapped[list[Any]] = mapped_column(JSON, default=list)


class PaymentAllocation(Base, TimestampMixin):
    """Explicit bill-wise allocation row (keeps Invoice.paid as cache)."""

    __tablename__ = "payment_allocations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    payment_id: Mapped[int] = mapped_column(ForeignKey("payments.id"), index=True)
    invoice_id: Mapped[Optional[int]] = mapped_column(ForeignKey("invoices.id"), nullable=True)
    purchase_invoice_id: Mapped[Optional[int]] = mapped_column(ForeignKey("purchase_invoices.id"), nullable=True)
    amount: Mapped[float] = mapped_column(Float, default=0)


# ??? Purchase ????????????????????????????????????????????????????????????????


class Vendor(Base, TimestampMixin):
    __tablename__ = "vendors"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    code: Mapped[str] = mapped_column(String(32))
    name: Mapped[str] = mapped_column(String(200))
    email: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    gstin: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    custom: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


class PurchaseOrder(Base, TimestampMixin):
    __tablename__ = "purchase_orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    number: Mapped[str] = mapped_column(String(40))
    vendor_id: Mapped[int] = mapped_column(ForeignKey("vendors.id"))
    status: Mapped[str] = mapped_column(String(32), default="draft")
    subtotal: Mapped[float] = mapped_column(Float, default=0)
    tax: Mapped[float] = mapped_column(Float, default=0)
    total: Mapped[float] = mapped_column(Float, default=0)
    lines: Mapped[list[Any]] = mapped_column(JSON, default=list)
    warehouse_id: Mapped[Optional[int]] = mapped_column(ForeignKey("warehouses.id"), nullable=True)
    custom: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


class GoodsReceipt(Base, TimestampMixin):
    __tablename__ = "goods_receipts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    number: Mapped[str] = mapped_column(String(40))
    purchase_order_id: Mapped[Optional[int]] = mapped_column(ForeignKey("purchase_orders.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="draft")
    lines: Mapped[list[Any]] = mapped_column(JSON, default=list)
    purchase_invoice_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    custom: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


class PurchaseInvoice(Base, TimestampMixin):
    __tablename__ = "purchase_invoices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    number: Mapped[str] = mapped_column(String(40))
    vendor_id: Mapped[int] = mapped_column(ForeignKey("vendors.id"))
    purchase_order_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("purchase_orders.id"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(32), default="draft")
    subtotal: Mapped[float] = mapped_column(Float, default=0)
    tax: Mapped[float] = mapped_column(Float, default=0)
    total: Mapped[float] = mapped_column(Float, default=0)
    paid: Mapped[float] = mapped_column(Float, default=0)
    lines: Mapped[list[Any]] = mapped_column(JSON, default=list)
    rcm: Mapped[bool] = mapped_column(Boolean, default=False)  # Reverse Charge Mechanism
    custom: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


# ??? Accounting ??????????????????????????????????????????????????????????????


class Account(Base, TimestampMixin):
    __tablename__ = "accounts"
    __table_args__ = (UniqueConstraint("company_id", "code"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    code: Mapped[str] = mapped_column(String(32))
    name: Mapped[str] = mapped_column(String(200))
    account_type: Mapped[str] = mapped_column(String(32))  # asset/liability/equity/income/expense
    parent_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    is_group: Mapped[bool] = mapped_column(Boolean, default=False)
    custom: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


class JournalEntry(Base, TimestampMixin):
    __tablename__ = "journal_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    number: Mapped[str] = mapped_column(String(40))
    entry_date: Mapped[date] = mapped_column(Date, default=date.today)
    narration: Mapped[str] = mapped_column(Text, default="")
    lines: Mapped[list[Any]] = mapped_column(JSON, default=list)  # [{account_id, debit, credit}]
    status: Mapped[str] = mapped_column(String(32), default="posted")
    # Kanha Books voucher types (own Tally-style desk)
    voucher_type: Mapped[str] = mapped_column(String(32), default="journal")
    party_name: Mapped[str] = mapped_column(String(200), default="")
    custom: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


class Budget(Base, TimestampMixin):
    __tablename__ = "budgets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    fiscal_year: Mapped[str] = mapped_column(String(16))
    lines: Mapped[list[Any]] = mapped_column(JSON, default=list)


class FixedAsset(Base, TimestampMixin):
    __tablename__ = "fixed_assets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    purchase_date: Mapped[date] = mapped_column(Date)
    cost: Mapped[float] = mapped_column(Float)
    depreciation_method: Mapped[str] = mapped_column(String(32), default="slm")
    useful_life_years: Mapped[int] = mapped_column(Integer, default=5)
    salvage: Mapped[float] = mapped_column(Float, default=0)


# ??? Manufacturing ???????????????????????????????????????????????????????????


class BOM(Base, TimestampMixin):
    __tablename__ = "boms"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))
    version: Mapped[str] = mapped_column(String(16), default="1.0")
    components: Mapped[list[Any]] = mapped_column(JSON, default=list)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class WorkOrder(Base, TimestampMixin):
    __tablename__ = "work_orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    number: Mapped[str] = mapped_column(String(40))
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))
    bom_id: Mapped[Optional[int]] = mapped_column(ForeignKey("boms.id"), nullable=True)
    qty: Mapped[float] = mapped_column(Float, default=1)
    status: Mapped[str] = mapped_column(String(32), default="planned")
    scheduled_start: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    scheduled_end: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    cost: Mapped[float] = mapped_column(Float, default=0)
    wip_value: Mapped[float] = mapped_column(Float, default=0)  # material parked in WIP


class Machine(Base, TimestampMixin):
    __tablename__ = "machines"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    code: Mapped[str] = mapped_column(String(32))
    name: Mapped[str] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(32), default="idle")


class QualityInspection(Base, TimestampMixin):
    __tablename__ = "quality_inspections"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    number: Mapped[str] = mapped_column(String(40))
    inspection_type: Mapped[str] = mapped_column(String(32))  # incoming/outgoing/process
    ref: Mapped[str] = mapped_column(String(64), default="")
    checklist: Mapped[list[Any]] = mapped_column(JSON, default=list)
    result: Mapped[str] = mapped_column(String(32), default="pending")  # pass/fail/pending
    capa: Mapped[str] = mapped_column(Text, default="")


# ??? HRMS ????????????????????????????????????????????????????????????????????


class Employee(Base, TimestampMixin):
    __tablename__ = "employees"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    code: Mapped[str] = mapped_column(String(32))
    full_name: Mapped[str] = mapped_column(String(200))
    email: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    department: Mapped[str] = mapped_column(String(100), default="")
    designation: Mapped[str] = mapped_column(String(100), default="")
    join_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    basic_salary: Mapped[float] = mapped_column(Float, default=0)
    shift: Mapped[str] = mapped_column(String(32), default="general")
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    # Salary bank payout
    bank_name: Mapped[str] = mapped_column(String(120), default="")
    bank_account: Mapped[str] = mapped_column(String(64), default="")
    ifsc: Mapped[str] = mapped_column(String(20), default="")
    # field / marketing / office
    work_type: Mapped[str] = mapped_column(String(32), default="office")
    track_live: Mapped[bool] = mapped_column(Boolean, default=False)
    custom: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


class Attendance(Base, TimestampMixin):
    __tablename__ = "attendance"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"))
    day: Mapped[date] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(16), default="present")
    check_in: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)
    check_out: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)
    source: Mapped[str] = mapped_column(String(32), default="manual")  # manual/biometric


class LeaveRequest(Base, TimestampMixin):
    __tablename__ = "leave_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"))
    leave_type: Mapped[str] = mapped_column(String(32), default="casual")
    from_date: Mapped[date] = mapped_column(Date)
    to_date: Mapped[date] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(32), default="pending")
    reason: Mapped[str] = mapped_column(Text, default="")


class EmployeeLoan(Base, TimestampMixin):
    """SBAC Employee Loan entry + approval — EMI deducted on payroll."""

    __tablename__ = "employee_loans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"), index=True)
    amount: Mapped[float] = mapped_column(Float, default=0)
    emi: Mapped[float] = mapped_column(Float, default=0)
    tenure_months: Mapped[int] = mapped_column(Integer, default=12)
    start_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="pending")  # pending/approved/active/closed/rejected
    purpose: Mapped[str] = mapped_column(String(200), default="")
    notes: Mapped[str] = mapped_column(Text, default="")
    custom: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


class PayrollRun(Base, TimestampMixin):
    __tablename__ = "payroll_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    period: Mapped[str] = mapped_column(String(16))  # 2026-07
    status: Mapped[str] = mapped_column(String(32), default="draft")
    lines: Mapped[list[Any]] = mapped_column(JSON, default=list)


class SalaryDisbursement(Base, TimestampMixin):
    """Bank salary payout batch (NEFT/IMPS/UPI link ready)."""

    __tablename__ = "salary_disbursements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    payroll_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    period: Mapped[str] = mapped_column(String(16), default="")
    status: Mapped[str] = mapped_column(String(32), default="draft")  # draft/queued/paid/failed
    mode: Mapped[str] = mapped_column(String(32), default="neft")
    total_amount: Mapped[float] = mapped_column(Float, default=0)
    lines: Mapped[list[Any]] = mapped_column(JSON, default=list)  # bank rows + UTR
    note: Mapped[str] = mapped_column(Text, default="")


class ExpenseClaim(Base, TimestampMixin):
    """Marketing / field staff expense claims + approval."""

    __tablename__ = "expense_claims"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"))
    claim_date: Mapped[date] = mapped_column(Date)
    category: Mapped[str] = mapped_column(String(64), default="travel")  # travel/food/client/misc
    amount: Mapped[float] = mapped_column(Float, default=0)
    description: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(32), default="pending")  # pending/approved/rejected/paid
    decided_by: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    decision_note: Mapped[str] = mapped_column(Text, default="")


class EmployeeLocation(Base, TimestampMixin):
    """Live field tracking pings (mobile GPS ? API)."""

    __tablename__ = "employee_locations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"), index=True)
    lat: Mapped[float] = mapped_column(Float, default=0)
    lng: Mapped[float] = mapped_column(Float, default=0)
    accuracy_m: Mapped[float] = mapped_column(Float, default=0)
    place_label: Mapped[str] = mapped_column(String(200), default="")
    battery_pct: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    recorded_at: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)


class EwayBill(Base, TimestampMixin):
    """E-Way Bill register ? NIC portal API wires at live with GSP keys."""

    __tablename__ = "eway_bills"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    number: Mapped[str] = mapped_column(String(32), default="")
    invoice_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    invoice_number: Mapped[str] = mapped_column(String(64), default="")
    doc_type: Mapped[str] = mapped_column(String(32), default="invoice")
    from_place: Mapped[str] = mapped_column(String(120), default="")
    to_place: Mapped[str] = mapped_column(String(120), default="")
    distance_km: Mapped[float] = mapped_column(Float, default=0)
    vehicle_no: Mapped[str] = mapped_column(String(32), default="")
    transporter: Mapped[str] = mapped_column(String(120), default="")
    status: Mapped[str] = mapped_column(String(32), default="draft")  # draft/generated/active/cancelled
    ewb_no: Mapped[str] = mapped_column(String(32), default="")
    valid_upto: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


# ??? Projects / Service ??????????????????????????????????????????????????????


class Project(Base, TimestampMixin):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    code: Mapped[str] = mapped_column(String(32))
    name: Mapped[str] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(32), default="active")
    progress: Mapped[int] = mapped_column(Integer, default=0)
    start_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    end_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)


class Task(Base, TimestampMixin):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"))
    title: Mapped[str] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(32), default="todo")  # todo/doing/done
    assignee_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    due_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    milestone: Mapped[str] = mapped_column(String(100), default="")


class ServiceTicket(Base, TimestampMixin):
    __tablename__ = "service_tickets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    number: Mapped[str] = mapped_column(String(40))
    customer_id: Mapped[Optional[int]] = mapped_column(ForeignKey("customers.id"), nullable=True)
    subject: Mapped[str] = mapped_column(String(200))
    ticket_type: Mapped[str] = mapped_column(String(32), default="complaint")  # amc/warranty/complaint
    status: Mapped[str] = mapped_column(String(32), default="open")
    engineer_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    visit_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    notes: Mapped[str] = mapped_column(Text, default="")


class Document(Base, TimestampMixin):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    entity: Mapped[str] = mapped_column(String(64), default="")
    entity_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    mime: Mapped[str] = mapped_column(String(64), default="application/pdf")
    path: Mapped[str] = mapped_column(String(500), default="")
    version: Mapped[int] = mapped_column(Integer, default=1)


class LookupMaster(Base, TimestampMixin):
    """Generic lookup for Brand / Group / Category / Unit / Transport / Agent / Country.
    V2 SaaS-safe: always scoped by company_id.
    """

    __tablename__ = "lookup_masters"
    __table_args__ = (UniqueConstraint("company_id", "master_type", "code"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    master_type: Mapped[str] = mapped_column(String(32), index=True)  # brand|unit|transport|…
    code: Mapped[str] = mapped_column(String(64))
    name: Mapped[str] = mapped_column(String(200))
    parent_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    custom: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


class ReportDefinition(Base, TimestampMixin):
    __tablename__ = "report_definitions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    code: Mapped[str] = mapped_column(String(64))
    name: Mapped[str] = mapped_column(String(200))
    module: Mapped[str] = mapped_column(String(64))
    query_config: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    is_system: Mapped[bool] = mapped_column(Boolean, default=True)


class AutomationJob(Base, TimestampMixin):
    __tablename__ = "automation_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    trigger: Mapped[str] = mapped_column(String(64))  # schedule/event
    action: Mapped[str] = mapped_column(String(64))  # email/whatsapp/sms/webhook
    config: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class WhatsAppTemplate(Base, TimestampMixin):
    """All WhatsApp message templates live in Automation ? auto-rendered by jobs."""

    __tablename__ = "whatsapp_templates"
    __table_args__ = (UniqueConstraint("company_id", "code"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    code: Mapped[str] = mapped_column(String(64), index=True)
    name: Mapped[str] = mapped_column(String(120), default="")
    category: Mapped[str] = mapped_column(String(64), default="general")  # sales|collection|ops|crm
    body: Mapped[str] = mapped_column(Text, default="")
    variables: Mapped[list[Any]] = mapped_column(JSON, default=list)  # ["name","amount"]
    language: Mapped[str] = mapped_column(String(16), default="hi")
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    auto_trigger: Mapped[str] = mapped_column(String(64), default="")  # lead_open|invoice_overdue|...
    meta: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


# --- Channel / Logistics / Batch / MRP ---


class PriceList(Base, TimestampMixin):
    __tablename__ = "price_lists"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    code: Mapped[str] = mapped_column(String(64))
    name: Mapped[str] = mapped_column(String(200))
    party_type: Mapped[str] = mapped_column(String(32), default="dealer")  # dealer/distributor/customer
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    lines: Mapped[list[Any]] = mapped_column(JSON, default=list)  # [{sku, product_id, price, discount_pct}]


class StockBatch(Base, TimestampMixin):
    __tablename__ = "stock_batches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))
    warehouse_id: Mapped[int] = mapped_column(ForeignKey("warehouses.id"))
    batch_no: Mapped[str] = mapped_column(String(64))
    qty: Mapped[float] = mapped_column(Float, default=0)
    mfg_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    expiry_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    notes: Mapped[str] = mapped_column(Text, default="")


class PackingList(Base, TimestampMixin):
    __tablename__ = "packing_lists"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    number: Mapped[str] = mapped_column(String(40))
    invoice_id: Mapped[Optional[int]] = mapped_column(ForeignKey("invoices.id"), nullable=True)
    customer_id: Mapped[Optional[int]] = mapped_column(ForeignKey("customers.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="draft")
    packages: Mapped[int] = mapped_column(Integer, default=1)
    weight_kg: Mapped[float] = mapped_column(Float, default=0)
    lines: Mapped[list[Any]] = mapped_column(JSON, default=list)


class DispatchChallan(Base, TimestampMixin):
    __tablename__ = "dispatch_challans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    number: Mapped[str] = mapped_column(String(40))
    packing_list_id: Mapped[Optional[int]] = mapped_column(ForeignKey("packing_lists.id"), nullable=True)
    invoice_id: Mapped[Optional[int]] = mapped_column(ForeignKey("invoices.id"), nullable=True)
    customer_id: Mapped[Optional[int]] = mapped_column(ForeignKey("customers.id"), nullable=True)
    transporter: Mapped[str] = mapped_column(String(120), default="")
    lr_number: Mapped[str] = mapped_column(String(64), default="")
    vehicle_no: Mapped[str] = mapped_column(String(32), default="")
    dispatch_date: Mapped[date] = mapped_column(Date, default=date.today)
    status: Mapped[str] = mapped_column(String(32), default="dispatched")
    notes: Mapped[str] = mapped_column(Text, default="")


class Einvoice(Base, TimestampMixin):
    __tablename__ = "einvoices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    invoice_id: Mapped[int] = mapped_column(ForeignKey("invoices.id"))
    irn: Mapped[str] = mapped_column(String(120), default="")
    ack_no: Mapped[str] = mapped_column(String(64), default="")
    ack_date: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="generated")  # generated/cancelled
    qr_payload: Mapped[str] = mapped_column(Text, default="")
    gsp_note: Mapped[str] = mapped_column(Text, default="Demo IRN ? live GSP wires at go-live")


class MrpPlan(Base, TimestampMixin):
    __tablename__ = "mrp_plans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    number: Mapped[str] = mapped_column(String(40))
    period: Mapped[str] = mapped_column(String(32))  # YYYY-MM
    status: Mapped[str] = mapped_column(String(32), default="draft")
    lines: Mapped[list[Any]] = mapped_column(JSON, default=list)  # shortage / suggest WO / PO
    notes: Mapped[str] = mapped_column(Text, default="")


class DealerOrder(Base, TimestampMixin):
    __tablename__ = "dealer_orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    number: Mapped[str] = mapped_column(String(40))
    dealer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"))
    status: Mapped[str] = mapped_column(String(32), default="submitted")  # submitted/approved/rejected/fulfilled
    lines: Mapped[list[Any]] = mapped_column(JSON, default=list)
    total: Mapped[float] = mapped_column(Float, default=0)
    notes: Mapped[str] = mapped_column(Text, default="")


# ??? Advanced differentiators: RFID + WhatsApp outbox ???????????????????????


class RfidTag(Base, TimestampMixin):
    __tablename__ = "rfid_tags"
    __table_args__ = (UniqueConstraint("company_id", "epc"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    epc: Mapped[str] = mapped_column(String(64), index=True)
    product_id: Mapped[Optional[int]] = mapped_column(ForeignKey("products.id"), nullable=True)
    warehouse_id: Mapped[Optional[int]] = mapped_column(ForeignKey("warehouses.id"), nullable=True)
    location_code: Mapped[str] = mapped_column(String(64), default="A-01")
    status: Mapped[str] = mapped_column(String(32), default="active")  # active/lost/retired
    last_scan_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    notes: Mapped[str] = mapped_column(Text, default="")


class RfidScan(Base):
    __tablename__ = "rfid_scans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    epc: Mapped[str] = mapped_column(String(64), index=True)
    action: Mapped[str] = mapped_column(String(32), default="locate")  # inbound/outbound/cycle/locate
    warehouse_id: Mapped[Optional[int]] = mapped_column(ForeignKey("warehouses.id"), nullable=True)
    product_id: Mapped[Optional[int]] = mapped_column(ForeignKey("products.id"), nullable=True)
    user_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class CommsMessage(Base, TimestampMixin):
    __tablename__ = "comms_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    channel: Mapped[str] = mapped_column(String(32), default="whatsapp")  # whatsapp/sms/email
    to_phone: Mapped[str] = mapped_column(String(40), default="")
    to_name: Mapped[str] = mapped_column(String(120), default="")
    template: Mapped[str] = mapped_column(String(64), default="custom")
    body: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(32), default="queued")  # queued/sent/failed
    related_entity: Mapped[str] = mapped_column(String(64), default="")
    related_id: Mapped[str] = mapped_column(String(64), default="")
    meta: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


# ?? HA cluster / multi-site resilience ???????????????????????????????????????


class ClusterNode(Base, TimestampMixin):
    __tablename__ = "cluster_nodes"
    __table_args__ = (UniqueConstraint("node_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    node_id: Mapped[str] = mapped_column(String(64), index=True)
    role: Mapped[str] = mapped_column(String(32), default="replica")  # primary|replica
    public_url: Mapped[str] = mapped_column(String(300), default="")
    priority: Mapped[int] = mapped_column(Integer, default=100)
    last_seq: Mapped[int] = mapped_column(Integer, default=0)
    last_checksum: Mapped[str] = mapped_column(String(128), default="")
    last_heartbeat: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="online")  # online|stale|offline|promoted
    meta: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


class SyncState(Base, TimestampMixin):
    __tablename__ = "sync_state"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    key: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    value: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


class SyncEvent(Base):
    """Append-only change log on primary ? replicas pull by seq (no duplicate apply)."""

    __tablename__ = "sync_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    seq: Mapped[int] = mapped_column(Integer, index=True)
    event_type: Mapped[str] = mapped_column(String(64), default="snapshot")  # snapshot|mutate|failover
    entity: Mapped[str] = mapped_column(String(64), default="")
    entity_id: Mapped[str] = mapped_column(String(64), default="")
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    checksum: Mapped[str] = mapped_column(String(128), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class FailedEntry(Base, TimestampMixin):
    """
    Entry/API crash auto-heal queue.
    Bad write is rolled back; payload kept so user can Re-enter without retyping.
    """

    __tablename__ = "failed_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[Optional[int]] = mapped_column(ForeignKey("companies.id"), nullable=True, index=True)
    user_email: Mapped[str] = mapped_column(String(200), default="", index=True)
    method: Mapped[str] = mapped_column(String(16), default="POST")
    path: Mapped[str] = mapped_column(String(400), default="", index=True)
    module_hint: Mapped[str] = mapped_column(String(64), default="")
    error_message: Mapped[str] = mapped_column(Text, default="")
    status_code: Mapped[int] = mapped_column(Integer, default=500)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    headers_safe: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    heal_status: Mapped[str] = mapped_column(String(32), default="pending")  # pending|healed|reentered|dismissed
    heal_note: Mapped[str] = mapped_column(Text, default="")
    healed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


class WorkDraft(Base, TimestampMixin):
    """
    Server-side draft ? phone lost / browser crash pe bhi form data company ke paas.
    Mobile/web app har few seconds sync kare; WhatsApp notes local mat rakho.
    """

    __tablename__ = "work_drafts"
    __table_args__ = (UniqueConstraint("company_id", "user_id", "draft_key"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    draft_key: Mapped[str] = mapped_column(String(120), index=True)  # e.g. sales.invoice.new
    module: Mapped[str] = mapped_column(String(64), default="")
    title: Mapped[str] = mapped_column(String(200), default="")
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    client: Mapped[str] = mapped_column(String(64), default="web")  # web|android|ios
    status: Mapped[str] = mapped_column(String(32), default="open")  # open|submitted|discarded


class DynamicRule(Base, TimestampMixin):
    """
    Scoped, time-based business rule ? future-proof without rewriting core code.
    AI may PROPOSE; human APPLY. Soft-delete + version history keep accuracy.
    """

    __tablename__ = "dynamic_rules"
    __table_args__ = (UniqueConstraint("company_id", "code", "version"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    code: Mapped[str] = mapped_column(String(80), index=True)
    name: Mapped[str] = mapped_column(String(200), default="")
    scope: Mapped[str] = mapped_column(String(64), index=True)
    description: Mapped[str] = mapped_column(Text, default="")
    conditions: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    actions: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    priority: Mapped[int] = mapped_column(Integer, default=100)
    version: Mapped[int] = mapped_column(Integer, default=1)
    effective_from: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    effective_to: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    months: Mapped[list[Any]] = mapped_column(JSON, default=list)
    weekdays: Mapped[list[Any]] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String(32), default="active")  # active|paused|retired
    source: Mapped[str] = mapped_column(String(32), default="manual")  # manual|ai_proposal|seed
    created_by: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)


class RuleProposal(Base, TimestampMixin):
    """AI / agent suggested rule ? never auto-mutates ERP until approved."""

    __tablename__ = "rule_proposals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    scope: Mapped[str] = mapped_column(String(64), default="")
    title: Mapped[str] = mapped_column(String(200), default="")
    rationale: Mapped[str] = mapped_column(Text, default="")
    proposed: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(32), default="pending")  # pending|approved|rejected
    created_by: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    reviewed_by: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    rule_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)


# ?? Live Monitor (stream-only ? NO DVR/video storage in ERP) ?????????????????


class MonitorSite(Base, TimestampMixin):
    """Office / plant / warehouse location for live watching."""

    __tablename__ = "monitor_sites"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    code: Mapped[str] = mapped_column(String(64), default="")
    name: Mapped[str] = mapped_column(String(200))
    city: Mapped[str] = mapped_column(String(100), default="")
    address: Mapped[str] = mapped_column(Text, default="")
    timezone: Mapped[str] = mapped_column(String(64), default="Asia/Kolkata")
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    notes: Mapped[str] = mapped_column(Text, default="")


class MonitorCamera(Base, TimestampMixin):
    """
    Camera = pointer to EXTERNAL stream (NVR/DVR/cloud cam).
    ERP does NOT store video bytes ? only URL + metadata for live view.
    """

    __tablename__ = "monitor_cameras"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    site_id: Mapped[int] = mapped_column(ForeignKey("monitor_sites.id"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    location_label: Mapped[str] = mapped_column(String(120), default="")  # Gate / Floor-2
    # https HLS / MJPEG / vendor embed / WebRTC gateway URL ? never upload MP4 here
    stream_url: Mapped[str] = mapped_column(Text, default="")
    embed_url: Mapped[str] = mapped_column(Text, default="")  # iframe-friendly viewer
    vendor: Mapped[str] = mapped_column(String(64), default="generic")  # hikvision|cpplus|generic
    kind: Mapped[str] = mapped_column(String(32), default="office")  # office|plant|employee_mobile|gate
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    meta: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


class MonitorChat(Base, TimestampMixin):
    """Live ops chat while watching a site ? text only, not video."""

    __tablename__ = "monitor_chats"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    site_id: Mapped[Optional[int]] = mapped_column(ForeignKey("monitor_sites.id"), nullable=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    body: Mapped[str] = mapped_column(Text, default="")
    to_user_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # optional DM

class ApprovalRequest(Base, TimestampMixin):
    """Hierarchy + emergency approval inbox ? module/dept control, bypass to admin."""

    __tablename__ = "approval_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    module: Mapped[str] = mapped_column(String(64), index=True)
    entity_type: Mapped[str] = mapped_column(String(64), default="")
    entity_id: Mapped[str] = mapped_column(String(64), default="")
    title: Mapped[str] = mapped_column(String(200), default="")
    amount: Mapped[float] = mapped_column(Float, default=0)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(32), default="pending", index=True)
    requested_by: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    required_level: Mapped[int] = mapped_column(Integer, default=2)
    current_level: Mapped[int] = mapped_column(Integer, default=1)
    emergency: Mapped[bool] = mapped_column(Boolean, default=False)
    emergency_reason: Mapped[str] = mapped_column(String(400), default="")
    decided_by: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    decided_at: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    decision_note: Mapped[str] = mapped_column(String(400), default="")


# --- Kanha field ops: visits / tasks / followups / PR / payment / indent ---


class FieldVisit(Base, TimestampMixin):
    __tablename__ = "field_visits"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    plan_no: Mapped[str] = mapped_column(String(40), default="")
    executive_name: Mapped[str] = mapped_column(String(120), default="")
    executive_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    customer_id: Mapped[Optional[int]] = mapped_column(ForeignKey("customers.id"), nullable=True)
    client_name: Mapped[str] = mapped_column(String(200), default="")
    contact_person: Mapped[str] = mapped_column(String(120), default="")
    purpose: Mapped[str] = mapped_column(String(400), default="")
    visit_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    visit_time: Mapped[str] = mapped_column(String(20), default="")
    status: Mapped[str] = mapped_column(String(32), default="planned")  # planned/done/cancelled
    notes: Mapped[str] = mapped_column(Text, default="")
    created_by: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)


class FieldTask(Base, TimestampMixin):
    """Standalone field/office task desk — not project kanban."""

    __tablename__ = "field_tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    title: Mapped[str] = mapped_column(Text, default="")
    assignee_name: Mapped[str] = mapped_column(String(120), default="")
    given_by: Mapped[str] = mapped_column(String(120), default="")
    client_name: Mapped[str] = mapped_column(String(200), default="")
    customer_id: Mapped[Optional[int]] = mapped_column(ForeignKey("customers.id"), nullable=True)
    priority: Mapped[str] = mapped_column(String(32), default="Medium")
    status: Mapped[str] = mapped_column(String(32), default="open")  # open/doing/done
    due_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    close_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    last_remark: Mapped[str] = mapped_column(String(400), default="")
    task_type: Mapped[str] = mapped_column(String(64), default="general")
    created_by: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)


class FollowUp(Base, TimestampMixin):
    __tablename__ = "follow_ups"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    followup_type: Mapped[str] = mapped_column(String(64), default="order")  # order/payment/lead/visit
    party_name: Mapped[str] = mapped_column(String(200), default="")
    customer_id: Mapped[Optional[int]] = mapped_column(ForeignKey("customers.id"), nullable=True)
    contact_person: Mapped[str] = mapped_column(String(120), default="")
    contact_no: Mapped[str] = mapped_column(String(40), default="")
    followup_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    next_followup_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    remarks: Mapped[str] = mapped_column(Text, default="")
    executive_name: Mapped[str] = mapped_column(String(120), default="")
    status: Mapped[str] = mapped_column(String(32), default="open")
    created_by: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)


class PurchaseRequisition(Base, TimestampMixin):
    __tablename__ = "purchase_requisitions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    number: Mapped[str] = mapped_column(String(40), default="")
    requested_by: Mapped[str] = mapped_column(String(120), default="")
    department: Mapped[str] = mapped_column(String(80), default="")
    status: Mapped[str] = mapped_column(String(32), default="pending")  # pending/approved/rejected/converted
    lines: Mapped[list[Any]] = mapped_column(JSON, default=list)
    notes: Mapped[str] = mapped_column(Text, default="")
    created_by: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)


class PaymentRequest(Base, TimestampMixin):
    __tablename__ = "payment_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    number: Mapped[str] = mapped_column(String(40), default="")
    party_name: Mapped[str] = mapped_column(String(200), default="")
    party_type: Mapped[str] = mapped_column(String(32), default="vendor")  # vendor/customer/other
    amount: Mapped[float] = mapped_column(Float, default=0)
    purpose: Mapped[str] = mapped_column(String(400), default="")
    status: Mapped[str] = mapped_column(String(32), default="pending")  # pending/approved/paid/rejected
    created_by: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)


class MaterialIndent(Base, TimestampMixin):
    __tablename__ = "material_indents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    number: Mapped[str] = mapped_column(String(40), default="")
    purpose: Mapped[str] = mapped_column(String(200), default="production")
    status: Mapped[str] = mapped_column(String(32), default="pending")  # pending/approved/issued
    lines: Mapped[list[Any]] = mapped_column(JSON, default=list)
    notes: Mapped[str] = mapped_column(Text, default="")
    created_by: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)


class VendorRateQuote(Base, TimestampMixin):
    """RFQ / supplier-wise rate for purchase."""

    __tablename__ = "vendor_rate_quotes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    vendor_name: Mapped[str] = mapped_column(String(200), default="")
    item_name: Mapped[str] = mapped_column(String(200), default="")
    rate: Mapped[float] = mapped_column(Float, default=0)
    qty: Mapped[float] = mapped_column(Float, default=1)
    uom: Mapped[str] = mapped_column(String(32), default="kg")
    status: Mapped[str] = mapped_column(String(32), default="active")
    notes: Mapped[str] = mapped_column(Text, default="")
    created_by: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)


class ProductionChallan(Base, TimestampMixin):
    """Shop-floor production challan from completed work order."""

    __tablename__ = "production_challans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    number: Mapped[str] = mapped_column(String(40), default="")
    work_order_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    product_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    warehouse_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    product_name: Mapped[str] = mapped_column(String(200), default="")
    qty: Mapped[float] = mapped_column(Float, default=0)
    status: Mapped[str] = mapped_column(String(32), default="issued")
    notes: Mapped[str] = mapped_column(Text, default="")
    created_by: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)


class CostCentre(Base, TimestampMixin):
    """Simple cost centre / department for voucher tagging."""

    __tablename__ = "cost_centres"
    __table_args__ = (UniqueConstraint("company_id", "code"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    code: Mapped[str] = mapped_column(String(32))
    name: Mapped[str] = mapped_column(String(120))
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class BankReconItem(Base, TimestampMixin):
    """Bank statement line for reconciliation against Kanha Books."""

    __tablename__ = "bank_recon_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    statement_date: Mapped[date] = mapped_column(Date, default=date.today)
    description: Mapped[str] = mapped_column(String(400), default="")
    amount: Mapped[float] = mapped_column(Float, default=0)  # +credit to bank / -debit
    matched_voucher_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="open")  # open/matched/ignored
    notes: Mapped[str] = mapped_column(Text, default="")
