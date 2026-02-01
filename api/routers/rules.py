"""
Rules Router - CRUD operations for forwarding rules
"""

from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status

from api.schemas import RuleCreate, RuleUpdate, RuleResponse, MessageResponse
from api.deps import get_db, get_current_user
from tgf.data.database import Database


router = APIRouter()


def _rule_to_response(rule_dict: Dict[str, Any]) -> RuleResponse:
    """Convert database rule dict to RuleResponse, mapping filters -> filter_text"""
    return RuleResponse(
        id=rule_dict['id'],
        name=rule_dict['name'],
        source_chat=rule_dict['source_chat'],
        target_chat=rule_dict['target_chat'],
        mode=rule_dict['mode'],
        interval_min=rule_dict['interval_min'],
        filter_text=rule_dict.get('filters'),  # Map 'filters' to 'filter_text'
        enabled=bool(rule_dict['enabled']),
        created_at=rule_dict.get('created_at'),
        updated_at=rule_dict.get('updated_at'),
    )


@router.get("", response_model=List[RuleResponse])
async def list_rules(
    enabled_only: bool = False,
    db: Database = Depends(get_db),
    _: str = Depends(get_current_user)
):
    """List all rules"""
    rules = await db.get_all_rules(enabled_only=enabled_only)
    return [_rule_to_response(r) for r in rules]


@router.post("", response_model=RuleResponse, status_code=status.HTTP_201_CREATED)
async def create_rule(
    rule: RuleCreate,
    db: Database = Depends(get_db),
    _: str = Depends(get_current_user)
):
    """Create a new rule"""
    # Check if name exists
    existing = await db.get_rule(name=rule.name)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Rule with name '{rule.name}' already exists"
        )
    
    rule_id = await db.create_rule(
        name=rule.name,
        source_chat=rule.source_chat,
        target_chat=rule.target_chat,
        mode=rule.mode,
        interval_min=rule.interval_min,
        filters=rule.filter_text,  # Map 'filter_text' to 'filters'
        enabled=rule.enabled
    )
    
    created = await db.get_rule(rule_id=rule_id)
    return _rule_to_response(created)


@router.get("/{rule_id}", response_model=RuleResponse)
async def get_rule(
    rule_id: int,
    db: Database = Depends(get_db),
    _: str = Depends(get_current_user)
):
    """Get a rule by ID"""
    rule = await db.get_rule(rule_id=rule_id)
    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Rule with ID {rule_id} not found"
        )
    return _rule_to_response(rule)


@router.put("/{rule_id}", response_model=RuleResponse)
async def update_rule(
    rule_id: int,
    updates: RuleUpdate,
    db: Database = Depends(get_db),
    _: str = Depends(get_current_user)
):
    """Update a rule"""
    existing = await db.get_rule(rule_id=rule_id)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Rule with ID {rule_id} not found"
        )
    
    # Build update dict with only provided fields
    update_data = updates.model_dump(exclude_unset=True)
    
    # Map 'filter_text' to 'filters' for database
    if 'filter_text' in update_data:
        update_data['filters'] = update_data.pop('filter_text')
    
    if update_data:
        await db.update_rule(rule_id, **update_data)
    
    updated = await db.get_rule(rule_id=rule_id)
    return _rule_to_response(updated)


@router.delete("/{rule_id}", response_model=MessageResponse)
async def delete_rule(
    rule_id: int,
    db: Database = Depends(get_db),
    _: str = Depends(get_current_user)
):
    """Delete a rule"""
    existing = await db.get_rule(rule_id=rule_id)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Rule with ID {rule_id} not found"
        )
    
    await db.delete_rule(rule_id=rule_id)
    return MessageResponse(message=f"Rule '{existing['name']}' deleted")


@router.post("/{rule_id}/enable", response_model=RuleResponse)
async def enable_rule(
    rule_id: int,
    db: Database = Depends(get_db),
    _: str = Depends(get_current_user)
):
    """Enable a rule"""
    existing = await db.get_rule(rule_id=rule_id)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Rule with ID {rule_id} not found"
        )
    
    await db.update_rule(rule_id, enabled=True)
    updated = await db.get_rule(rule_id=rule_id)
    return _rule_to_response(updated)


@router.post("/{rule_id}/disable", response_model=RuleResponse)
async def disable_rule(
    rule_id: int,
    db: Database = Depends(get_db),
    _: str = Depends(get_current_user)
):
    """Disable a rule"""
    existing = await db.get_rule(rule_id=rule_id)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Rule with ID {rule_id} not found"
        )
    
    await db.update_rule(rule_id, enabled=False)
    updated = await db.get_rule(rule_id=rule_id)
    return _rule_to_response(updated)
