from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session
from typing import Dict, List, Any
from app.database import get_db
from app.auth import get_current_user
from app import models, schemas

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

@router.get("/stats", response_model=schemas.DashboardStats)
def get_dashboard_stats(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    # Fetch all session IDs for the user
    user_sessions = db.query(models.ChatSession.id, models.ChatSession.mode).filter(
        models.ChatSession.user_id == current_user.id
    ).all()
    
    session_ids = [s.id for s in user_sessions]
    total_sessions = len(session_ids)
    
    # Initialize defaults
    avg_grammar = 0.0
    avg_vocab = 0.0
    avg_fluency = 0.0
    total_messages = 0
    mode_counts = {
        "casual": 0,
        "interview": 0,
        "ielts": 0,
        "business": 0,
        "daily": 0
    }
    score_progress = []
    
    # Calculate mode counts
    for s in user_sessions:
        m = s.mode.lower()
        if m in mode_counts:
            mode_counts[m] += 1
            
    if total_sessions > 0:
        # Fetch score averages from messages in user's sessions
        # Only analyze messages with non-null scores (which are user messages processed by LLM)
        scores_query = db.query(
            func.avg(models.Message.grammar_score).label("avg_g"),
            func.avg(models.Message.vocabulary_score).label("avg_v"),
            func.avg(models.Message.fluency_score).label("avg_f"),
            func.count(models.Message.id).label("total_msg")
        ).filter(
            models.Message.session_id.in_(session_ids),
            models.Message.grammar_score.isnot(None)
        ).first()
        
        if scores_query and scores_query.total_msg > 0:
            avg_grammar = float(scores_query.avg_g) if scores_query.avg_g else 0.0
            avg_vocab = float(scores_query.avg_v) if scores_query.avg_v else 0.0
            avg_fluency = float(scores_query.avg_f) if scores_query.avg_f else 0.0
            total_messages = int(scores_query.total_msg)

        # Get chronological progress data for score charting
        # Group by day and get average scores
        progress_query = db.query(
            func.date(models.Message.created_at).label("day"),
            func.avg(models.Message.grammar_score).label("avg_g"),
            func.avg(models.Message.vocabulary_score).label("avg_v"),
            func.avg(models.Message.fluency_score).label("avg_f")
        ).filter(
            models.Message.session_id.in_(session_ids),
            models.Message.grammar_score.isnot(None)
        ).group_by(
            func.date(models.Message.created_at)
        ).order_by(
            "day"
        ).all()
        
        for p in progress_query:
            score_progress.append({
                "date": str(p.day),
                "grammar": round(float(p.avg_g), 1) if p.avg_g else 0.0,
                "vocabulary": round(float(p.avg_v), 1) if p.avg_v else 0.0,
                "fluency": round(float(p.avg_f), 1) if p.avg_f else 0.0
            })
            
    # Round averages
    avg_grammar = round(avg_grammar, 1)
    avg_vocab = round(avg_vocab, 1)
    avg_fluency = round(avg_fluency, 1)

    return schemas.DashboardStats(
        avg_grammar_score=avg_grammar,
        avg_vocabulary_score=avg_vocab,
        avg_fluency_score=avg_fluency,
        total_sessions=total_sessions,
        total_messages=total_messages,
        mode_counts=mode_counts,
        score_progress=score_progress
    )
