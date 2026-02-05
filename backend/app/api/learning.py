from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from openai import AsyncOpenAI
import json

from ..database import get_db
from ..models import LearningRecord, User, ChatMessage, ChatSession
from ..middleware.auth import verify_token
from ..config import settings

router = APIRouter()

class LearningEvent(BaseModel):
    event_type: str
    content: Optional[str] = None
    score: Optional[int] = None

class DashboardStats(BaseModel):
    total_logins: int
    questions_asked: int
    quiz_average: float
    recent_activity: List[dict]
    ai_analysis: str

@router.post("/track")
async def track_learning_event(
    event: LearningEvent,
    token: dict = Depends(verify_token),
    db: Session = Depends(get_db)
):
    user_id = token.get("sub")
    record = LearningRecord(
        user_id=user_id,
        event_type=event.event_type,
        content=event.content,
        score=event.score
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return {"status": "success", "id": record.id}

@router.get("/dashboard")
async def get_dashboard_data(
    token: dict = Depends(verify_token),
    db: Session = Depends(get_db)
):
    user_id = token.get("sub")
    
    # 1. Basic Stats
    logins = db.query(LearningRecord).filter(
        LearningRecord.user_id == user_id, 
        LearningRecord.event_type == 'login'
    ).count()
    
    # Count questions from ChatMessage (linked via ChatSession)
    questions = db.query(ChatMessage).join(ChatSession).filter(
        ChatSession.user_id == user_id,
        ChatMessage.role == 'user'
    ).count()
    
    # Quiz scores (mock or real)
    quiz_records = db.query(LearningRecord).filter(
        LearningRecord.user_id == user_id,
        LearningRecord.event_type == 'quiz_result'
    ).all()
    
    quiz_avg = 0
    if quiz_records:
        scores = [r.score for r in quiz_records if r.score is not None]
        if scores:
            quiz_avg = sum(scores) / len(scores)

    # 2. Recent Activity
    recent_records = db.query(LearningRecord).filter(
        LearningRecord.user_id == user_id
    ).order_by(LearningRecord.created_at.desc()).limit(10).all()
    
    activity_log = [
        {
            "type": r.event_type,
            "content": r.content,
            "score": r.score,
            "date": r.created_at.strftime("%Y-%m-%d %H:%M")
        }
        for r in recent_records
    ]

    # 3. AI Analysis
    last_analysis = db.query(LearningRecord).filter(
        LearningRecord.user_id == user_id,
        LearningRecord.event_type == 'ai_analysis'
    ).order_by(LearningRecord.created_at.desc()).first()
    
    analysis_text = last_analysis.content if last_analysis else "暂无分析数据，请点击生成。"

    return {
        "total_logins": logins,
        "questions_asked": questions,
        "quiz_average": round(quiz_avg, 1),
        "recent_activity": activity_log,
        "ai_analysis": analysis_text
    }

@router.post("/analyze")
async def generate_analysis(
    token: dict = Depends(verify_token),
    db: Session = Depends(get_db)
):
    user_id = token.get("sub")
    
    # Gather context
    last_questions = db.query(ChatMessage.content).join(ChatSession).filter(
        ChatSession.user_id == user_id,
        ChatMessage.role == 'user'
    ).order_by(ChatMessage.created_at.desc()).limit(20).all()
    
    question_text = "\n".join([q[0] for q in last_questions]) if last_questions else "暂无提问记录"
    
    quizzes = db.query(LearningRecord).filter(
        LearningRecord.user_id == user_id,
        LearningRecord.event_type == 'quiz_result'
    ).all()
    quiz_text = "\n".join([f"分数: {q.score} (详情: {q.content})" for q in quizzes]) if quizzes else "暂无测验记录"

    prompt = f"""
    请根据以下学员数据生成一份简短的学习分析报告（Markdown格式）。
    
    [最近提问]
    {question_text}
    
    [测验成绩]
    {quiz_text}
    
    请包含：
    1. 学习兴趣点（基于提问）
    2. 薄弱环节（基于低分测验或重复提问）
    3. 学习建议
    """

    try:
        client = AsyncOpenAI(
            api_key=settings.LLM_API_KEY,
            base_url=settings.LLM_BASE_URL
        )
        
        response = await client.chat.completions.create(
            model=settings.LLM_MODEL_NAME,
            messages=[{"role": "user", "content": prompt}]
        )
        
        analysis = response.choices[0].message.content
        
        # Save analysis
        record = LearningRecord(
            user_id=user_id,
            event_type='ai_analysis',
            content=analysis
        )
        db.add(record)
        db.commit()
        
        return {"analysis": analysis}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
