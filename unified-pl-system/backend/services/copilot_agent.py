import google.generativeai as genai
import pandas as pd
from sqlalchemy.orm import Session

from config import settings
from models.pl_record import PLRecord

if settings.GEMINI_API_KEY:
    genai.configure(api_key=settings.GEMINI_API_KEY)
    model = genai.GenerativeModel("gemini-pro")
else:
    model = None


def get_rag_context(db: Session, question: str) -> str:
    # Basic keyword-based context retrieval for the POC RAG
    # In a full enterprise setting with pgvector, we would vectorize the question
    # and do a cosine similarity search over a Document table.
    # Here, we pull recent P&L stats as context.

    records = db.query(PLRecord).order_by(PLRecord.created_at.desc()).limit(100).all()
    if not records:
        return "No financial data available."

    df = pd.DataFrame(
        [
            {
                "domain": r.domain,
                "period": r.period,
                "line_item": r.line_item,
                "amount": r.amount,
            }
            for r in records
        ]
    )

    context = "Recent P&L Summary:\n"
    domain_totals = df.groupby("domain")["amount"].sum().to_dict()
    for d, t in domain_totals.items():
        context += f"- {d} Total Amount: {t}\n"

    return context


def ask_copilot(db: Session, question: str) -> str:
    if not model:
        return "Gemini API key is not configured. Please set GEMINI_API_KEY in the environment."

    context = get_rag_context(db, question)

    prompt = f"""
    You are an expert AI Financial Copilot. 
    Use the following context from our P&L database to answer the user's question. 
    If the answer is not in the context, you can provide general financial advice, but clarify that you lack specific data.
    
    Context:
    {context}
    
    Question: {question}
    """

    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Error connecting to Gemini: {str(e)}"
