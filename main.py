import os
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

from database import db, create_document, get_documents
from schemas import Invoice, BankTransaction, Match

app = FastAPI(title="Bookkeeping Automation API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "Bookkeeping Automation API running"}

@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }
    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
            response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
                response["connection_status"] = "Connected"
            except Exception as e:
                response["database"] = f"⚠️ Connected but Error: {str(e)[:80]}"
        else:
            response["database"] = "⚠️ Available but not initialized"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:80]}"
    return response

# ------------------------------------------------------
# Minimal parsing logic: we won't do real OCR, but accept
# uploaded invoice metadata via JSON and store it.
# ------------------------------------------------------

class InvoiceCreate(Invoice):
    pass

class BankTransactionCreate(BankTransaction):
    pass

class MatchResult(BaseModel):
    invoice_number: str
    bank_transaction_id: str
    confidence: float
    reason: Optional[str] = None

@app.post("/invoices", response_model=dict)
async def create_invoice(invoice: InvoiceCreate):
    try:
        inserted_id = create_document("invoice", invoice)
        return {"id": inserted_id, "status": "created"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/invoices", response_model=List[dict])
async def list_invoices():
    try:
        docs = get_documents("invoice", {}, limit=100)
        # convert ObjectId to string
        return [
            {**{k: (str(v) if k == "_id" else v) for k, v in d.items()}}
            for d in docs
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/bank-transactions", response_model=dict)
async def create_bank_txn(txn: BankTransactionCreate):
    try:
        inserted_id = create_document("banktransaction", txn)
        return {"id": inserted_id, "status": "created"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/bank-transactions", response_model=List[dict])
async def list_bank_txns():
    try:
        docs = get_documents("banktransaction", {}, limit=200)
        return [
            {**{k: (str(v) if k == "_id" else v) for k, v in d.items()}}
            for d in docs
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Simple matching logic: match by total amount and closest date within 7 days
@app.post("/match", response_model=List[MatchResult])
async def match_invoices_to_bank():
    try:
        invoices = get_documents("invoice", {}, limit=500)
        txns = get_documents("banktransaction", {}, limit=1000)
        results: List[MatchResult] = []

        # Preprocess txns by amount
        from collections import defaultdict
        txns_by_amount = defaultdict(list)
        for t in txns:
            txns_by_amount[round(float(t.get("amount", 0)), 2)].append(t)

        for inv in invoices:
            inv_total = round(float(inv.get("total", 0)), 2)
            candidates = txns_by_amount.get(inv_total, [])
            best = None
            best_score = -1.0
            reason = None

            inv_date = inv.get("invoice_date")
            if isinstance(inv_date, str):
                try:
                    inv_date = datetime.fromisoformat(inv_date)
                except Exception:
                    inv_date = None

            for t in candidates:
                t_date = t.get("date")
                if isinstance(t_date, str):
                    try:
                        t_date = datetime.fromisoformat(t_date)
                    except Exception:
                        t_date = None

                score = 0.6  # base score for amount match
                if inv_date and t_date:
                    days = abs((t_date.date() - inv_date.date()).days)
                    if days <= 7:
                        score += 0.4
                        reason = f"Amount matches and dates within {days} days"
                    else:
                        reason = f"Amount matches but dates {days} days apart"
                else:
                    reason = "Amount matches"

                if score > best_score:
                    best_score = score
                    best = t

            if best is not None:
                results.append(MatchResult(
                    invoice_number=inv.get("invoice_number", ""),
                    bank_transaction_id=str(best.get("_id")),
                    confidence=round(best_score, 2),
                    reason=reason
                ))

        # Optionally store matches
        for r in results:
            create_document("match", {
                "invoice_number": r.invoice_number,
                "bank_transaction_id": r.bank_transaction_id,
                "confidence": r.confidence,
                "reason": r.reason
            })

        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
