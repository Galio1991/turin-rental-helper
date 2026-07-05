#!/usr/bin/env python3
"""
工具函数
"""


def format_price(price: float) -> str:
    """格式化价格"""
    return f"€{price:.0f}"


def format_listing_summary(listing: Dict) -> str:
    """格式化房源摘要"""
    parts = []

    if listing.get('price'):
        parts.append(f"€{listing['price']:.0f}/月")

    if listing.get('area'):
        parts.append(f"{listing['area']}m²")

    if listing.get('district'):
        parts.append(listing['district'])

    return ' | '.join(parts)


def generate_recommendation_reason(listing: Dict, user_preferences: Dict) -> str:
    """
    生成推荐理由

    Args:
        listing: 房源信息
        user_preferences: 用户偏好

    Returns:
        推荐理由文本
    """
    reasons = []

    # 价格优势
    max_price = user_preferences.get('max_price', 0)
    price = listing.get('price', 0)
    if max_price and price <= max_price * 0.85:
        reasons.append(f"价格低于预算{((max_price - price) / max_price * 100):.0f}%")

    # 位置优势
    preferred_districts = user_preferences.get('preferred_districts', [])
    if listing.get('district') in preferred_districts:
        reasons.append(f"位于首选区域{listing['district']}")

    # 设施优势
    if listing.get('furnished'):
        reasons.append("带家具")
    if listing.get('has_ac'):
        reasons.append("有空调")
    if listing.get('heating') == 'independent':
        reasons.append("独立供暖")

    # 安全性
    safe_districts = ['Cit Turin', 'Crocetta', 'Centro']
    if listing.get('district') in safe_districts:
        reasons.append("安全区域")

    return '；'.join(reasons) if reasons else "综合条件符合需求"
