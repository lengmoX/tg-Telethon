"""
States Router - View sync states for rules
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException

from api.schemas import StateResponse
from api.deps import get_db, get_current_user
from tgf.data.database import Database


router = APIRouter()


@router.get("", response_model=List[StateResponse])
async def list_states(
    db: Database = Depends(get_db),
    _: str = Depends(get_current_user)
):
    """List all rule states"""
    rules = await db.get_all_rules()
    states = []
    
    for rule in rules:
        state = await db.get_state(rule['id'], 'default')
        states.append(StateResponse(
            rule_id=rule['id'],
            rule_name=rule['name'],
            namespace='default',
            last_msg_id=state['last_msg_id'] if state else 0,
            total_forwarded=state['total_forwarded'] if state else 0,
            last_sync_at=state['last_sync_at'] if state else None
        ))
    
    return states


@router.get("/{rule_id}", response_model=StateResponse)
async def get_state(
    rule_id: int,
    db: Database = Depends(get_db),
    _: str = Depends(get_current_user)
):
    """Get state for a specific rule"""
    rule = await db.get_rule(id=rule_id)
    if not rule:
        raise HTTPException(
            status_code=404,
            detail=f"Rule with ID {rule_id} not found"
        )
    
    state = await db.get_state(rule_id, 'default')
    
    return StateResponse(
        rule_id=rule_id,
        rule_name=rule['name'],
        namespace='default',
        last_msg_id=state['last_msg_id'] if state else 0,
        total_forwarded=state['total_forwarded'] if state else 0,
        last_sync_at=state['last_sync_at'] if state else None
    )
