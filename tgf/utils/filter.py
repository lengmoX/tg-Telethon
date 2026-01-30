"""
Message Filter Engine for TGF

Provides filtering capabilities for messages based on text patterns.
Supports per-rule filters and global filters.
"""

import re
import json
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field
from enum import Enum


class FilterAction(Enum):
    """What to do when filter matches"""
    EXCLUDE = "exclude"  # Skip the message
    INCLUDE = "include"  # Force include (override excludes)


class FilterType(Enum):
    """Type of filter matching"""
    CONTAINS = "contains"     # Simple substring match
    REGEX = "regex"           # Regular expression
    STARTS_WITH = "starts"    # Message starts with
    ENDS_WITH = "ends"        # Message ends with
    KEYWORD = "keyword"       # Word boundary match


@dataclass
class FilterRule:
    """A single filter rule"""
    pattern: str
    action: FilterAction = FilterAction.EXCLUDE
    filter_type: FilterType = FilterType.CONTAINS
    case_sensitive: bool = False
    enabled: bool = True
    name: Optional[str] = None
    
    def matches(self, text: str) -> bool:
        """Check if pattern matches the text"""
        if not self.enabled or not text:
            return False
        
        pattern = self.pattern
        check_text = text if self.case_sensitive else text.lower()
        check_pattern = pattern if self.case_sensitive else pattern.lower()
        
        if self.filter_type == FilterType.CONTAINS:
            return check_pattern in check_text
        
        elif self.filter_type == FilterType.STARTS_WITH:
            return check_text.startswith(check_pattern)
        
        elif self.filter_type == FilterType.ENDS_WITH:
            return check_text.endswith(check_pattern)
        
        elif self.filter_type == FilterType.KEYWORD:
            # Word boundary match
            flags = 0 if self.case_sensitive else re.IGNORECASE
            word_pattern = r'\b' + re.escape(pattern) + r'\b'
            return bool(re.search(word_pattern, text, flags))
        
        elif self.filter_type == FilterType.REGEX:
            try:
                flags = 0 if self.case_sensitive else re.IGNORECASE
                return bool(re.search(pattern, text, flags))
            except re.error:
                return False
        
        return False
    
    def to_dict(self) -> dict:
        """Convert to dictionary for storage"""
        return {
            "pattern": self.pattern,
            "action": self.action.value,
            "type": self.filter_type.value,
            "case_sensitive": self.case_sensitive,
            "enabled": self.enabled,
            "name": self.name,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "FilterRule":
        """Create from dictionary"""
        return cls(
            pattern=data.get("pattern", ""),
            action=FilterAction(data.get("action", "exclude")),
            filter_type=FilterType(data.get("type", "contains")),
            case_sensitive=data.get("case_sensitive", False),
            enabled=data.get("enabled", True),
            name=data.get("name"),
        )


@dataclass
class FilterConfig:
    """Complete filter configuration"""
    rules: List[FilterRule] = field(default_factory=list)
    
    def add_rule(self, rule: FilterRule) -> None:
        """Add a filter rule"""
        self.rules.append(rule)
    
    def add_exclude(
        self,
        pattern: str,
        filter_type: FilterType = FilterType.CONTAINS,
        case_sensitive: bool = False,
        name: Optional[str] = None
    ) -> None:
        """Add an exclude filter"""
        self.rules.append(FilterRule(
            pattern=pattern,
            action=FilterAction.EXCLUDE,
            filter_type=filter_type,
            case_sensitive=case_sensitive,
            name=name
        ))
    
    def add_include(
        self,
        pattern: str,
        filter_type: FilterType = FilterType.CONTAINS,
        case_sensitive: bool = False,
        name: Optional[str] = None
    ) -> None:
        """Add an include filter (overrides excludes)"""
        self.rules.append(FilterRule(
            pattern=pattern,
            action=FilterAction.INCLUDE,
            filter_type=filter_type,
            case_sensitive=case_sensitive,
            name=name
        ))
    
    def remove_rule(self, index: int) -> bool:
        """Remove a rule by index"""
        if 0 <= index < len(self.rules):
            self.rules.pop(index)
            return True
        return False
    
    def to_json(self) -> str:
        """Serialize to JSON string"""
        return json.dumps([r.to_dict() for r in self.rules], ensure_ascii=False)
    
    @classmethod
    def from_json(cls, json_str: Optional[str]) -> "FilterConfig":
        """Create from JSON string"""
        if not json_str:
            return cls()
        
        try:
            data = json.loads(json_str)
            rules = [FilterRule.from_dict(r) for r in data]
            return cls(rules=rules)
        except (json.JSONDecodeError, TypeError):
            return cls()


class MessageFilter:
    """
    Message filter that combines rule-specific and global filters.
    
    Filter logic:
    1. If any INCLUDE filter matches -> PASS (override excludes)
    2. If any EXCLUDE filter matches -> BLOCK
    3. Otherwise -> PASS
    """
    
    def __init__(
        self,
        rule_filters: Optional[FilterConfig] = None,
        global_filters: Optional[FilterConfig] = None
    ):
        self.rule_filters = rule_filters or FilterConfig()
        self.global_filters = global_filters or FilterConfig()
    
    def should_forward(self, message_text: str) -> tuple[bool, Optional[str]]:
        """
        Check if message should be forwarded.
        
        Returns:
            Tuple of (should_forward, reason)
            - (True, None) if message passes
            - (False, reason) if message is blocked
        """
        if not message_text:
            return (True, None)
        
        # Combine all filters
        all_rules = self.global_filters.rules + self.rule_filters.rules
        
        # First check includes (they override excludes)
        for rule in all_rules:
            if rule.action == FilterAction.INCLUDE and rule.matches(message_text):
                return (True, None)
        
        # Then check excludes
        for rule in all_rules:
            if rule.action == FilterAction.EXCLUDE and rule.matches(message_text):
                reason = f"Blocked by filter: {rule.name or rule.pattern}"
                return (False, reason)
        
        # No filter matched -> pass
        return (True, None)
    
    def filter_messages(self, messages: List[Any], get_text: callable = None) -> List[Any]:
        """
        Filter a list of messages.
        
        Args:
            messages: List of message objects
            get_text: Function to extract text from message (default: msg.text)
        
        Returns:
            Filtered list of messages that passed all filters
        """
        if get_text is None:
            get_text = lambda msg: getattr(msg, 'text', '') or ''
        
        result = []
        for msg in messages:
            text = get_text(msg)
            should_pass, _ = self.should_forward(text)
            if should_pass:
                result.append(msg)
        
        return result


def parse_filter_string(filter_str: str) -> FilterConfig:
    """
    Parse a simple filter string format for CLI.
    
    Format: "pattern1;pattern2;!include_pattern"
    - Prefix with ! to make it an include filter
    - Separate multiple patterns with ;
    
    Examples:
        "广告;推广"         -> Exclude messages containing 广告 or 推广
        "广告;!重要"        -> Exclude 广告, but if contains 重要 still forward
    """
    config = FilterConfig()
    
    if not filter_str:
        return config
    
    patterns = [p.strip() for p in filter_str.split(';') if p.strip()]
    
    for pattern in patterns:
        if pattern.startswith('!'):
            # Include filter
            config.add_include(pattern[1:])
        else:
            # Exclude filter
            config.add_exclude(pattern)
    
    return config
