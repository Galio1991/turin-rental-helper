#!/usr/bin/env python3
"""
房源爬虫模块
多区域广撒网搜索，动态权重评分
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Optional


# 区域数据缓存
_districts_data = None


def load_districts_data() -> Dict:
    """加载区域数据"""
    global _districts_data
    if _districts_data is None:
        data_path = Path(__file__).parent.parent / "assets" / "data" / "turin-districts.json"
        if data_path.exists():
            with open(data_path, 'r', encoding='utf-8') as f:
                _districts_data = json.load(f)
        else:
            _districts_data = {"districts": {}}
    return _districts_data


def get_search_districts(user_preferences: Dict) -> List[str]:
    """
    根据用户偏好动态确定搜索区域列表
    
    Args:
        user_preferences: 用户偏好
        
    Returns:
        推荐搜索的区域列表
    """
    districts_data = load_districts_data()
    all_districts = districts_data.get('districts', {})
    
    # 用户指定的优先区域
    preferred = user_preferences.get('preferred_districts', [])
    
    # 获取安全区域列表
    safe_districts = []
    for name, info in all_districts.items():
        safety = info.get('safety_score', 0)
        if safety >= 6.0:  # 安全评分6分以上
            safe_districts.append(name)
    
    # 根据用户偏好排序
    priority_districts = []
    secondary_districts = []
    
    for district in safe_districts:
        if district in preferred:
            priority_districts.append(district)
        else:
            secondary_districts.append(district)
    
    # 返回优先区域 + 其他安全区域
    return priority_districts + secondary_districts


def extract_listings_from_text(text: str, website: str = 'idealista', target_district: str = '') -> List[Dict]:
    """
    从爬取的文本中提取房源信息
    
    Args:
        text: 爬取的页面内容
        website: 来源网站
        target_district: 目标区域
        
    Returns:
        房源列表
    """
    listings = []
    
    # 提取房源块
    blocks = re.split(r'\n(?=\[.*?\]\(https://www\.idealista\.it/immobile/)', text)
    
    for block in blocks:
        listing = extract_single_listing(block, website, target_district)
        if listing and listing.get('price'):
            listings.append(listing)
    
    return listings


def extract_single_listing(text: str, website: str, target_district: str = '') -> Optional[Dict]:
    """
    提取单个房源信息
    """
    listing = {}
    
    # 提取链接和标题
    link_match = re.search(r'\[(.*?)\]\((https://www\.idealista\.it/immobile/\d+/)', text)
    if link_match:
        listing['title'] = link_match.group(1)
        listing['url'] = link_match.group(2)
    else:
        return None
    
    # 提取价格
    price_match = re.search(r'(\d[\d.,]*)\s*€/mese', text)
    if price_match:
        listing['price'] = parse_price(price_match.group(1))
    else:
        return None
    
    # 提取面积
    area_match = re.search(r'(\d+)\s*m²', text)
    if area_match:
        listing['area'] = int(area_match.group(1))
    
    # 提取房间数
    rooms_match = re.search(r'(\d+)\s*locali', text)
    if rooms_match:
        listing['rooms'] = int(rooms_match.group(1))
    
    # 提取位置
    listing['district'] = detect_district(text) or target_district
    
    # 检测房型
    if 'monolocale' in text.lower() or '1 locale' in text:
        listing['type'] = 'studio'
    elif 'bilocale' in text.lower() or '2 locali' in text:
        listing['type'] = 'bilocale'
    elif 'trilocale' in text.lower() or '3 locali' in text:
        listing['type'] = 'trilocale'
    elif 'camera' in text.lower() or 'stanza' in text.lower():
        listing['type'] = 'room'
    else:
        listing['type'] = 'apartment'
    
    # 检测设施
    listing['has_ac'] = 'aria condizionata' in text.lower() or 'climatizzatore' in text.lower()
    listing['has_elevator'] = 'ascensore' in text.lower()
    listing['furnished'] = 'arredato' in text.lower() or 'arredata' in text.lower()
    
    # 检测暖气类型
    if 'riscaldamento autonomo' in text.lower() or 'autonomo' in text.lower():
        listing['heating'] = 'independent'
    elif 'riscaldamento centralizzato' in text.lower() or 'centralizzato' in text.lower():
        listing['heating'] = 'centralized'
    else:
        listing['heating'] = 'unknown'
    
    return listing


def detect_district(text: str) -> str:
    """从文本中检测区域"""
    districts_map = {
        'Cit Turin': ['cit turin', 'citturin'],
        'Crocetta': ['crocetta'],
        'Centro': ['centro', 'centro storico'],
        'Cenisia': ['cenisia'],
        'San Donato': ['san donato'],
        'Borgo Po': ['borgo po', 'gran madre'],
        'San Salvario': ['san salvario'],
        'Aurora': ['aurora'],
        'Barriera di Milano': ['barriera di milano', 'barriera'],
        'Vanchiglia': ['vanchiglia'],
        'Campidoglio': ['campidoglio'],
        'Borgo San Paolo': ['borgo san paolo', 'san paolo'],
        'Valdocco': ['valdocco'],
        'Madonna di Campagna': ['madonna di campagna'],
        'Mirafiori Nord': ['mirafiori nord'],
        'Mirafiori Sud': ['mirafiori sud']
    }
    
    text_lower = text.lower()
    for district, keywords in districts_map.items():
        for keyword in keywords:
            if keyword in text_lower:
                return district
    
    return ''


def parse_price(price_str: str) -> float:
    """解析价格字符串"""
    price_str = price_str.replace('.', '').replace(',', '.')
    try:
        return float(price_str)
    except ValueError:
        return 0


def filter_listings(
    listings: List[Dict],
    user_preferences: Dict
) -> List[Dict]:
    """
    根据用户偏好筛选房源（更灵活的筛选）
    """
    max_price = user_preferences.get('max_price', float('inf'))
    room_type = user_preferences.get('room_type')
    furnished = user_preferences.get('furnished')
    
    # 危险区域列表（只排除真正危险的区域）
    dangerous_districts = ['Aurora', 'Barriera di Milano', 'Porta Palazzo']
    
    filtered = []
    for listing in listings:
        # 价格筛选（必须）
        if listing.get('price', 0) > max_price:
            continue
        
        # 排除危险区域
        if listing.get('district') in dangerous_districts:
            continue
        
        # 房型筛选（软性）
        if room_type and listing.get('type') != room_type:
            # 如果用户要studio但找到的是bilocale，仍然保留但降低评分
            pass
        
        # 家具筛选（软性）
        if furnished is not None and listing.get('furnished') != furnished:
            # 不完全排除，但降低评分
            pass
        
        filtered.append(listing)
    
    return filtered


def score_listing(listing: Dict, user_preferences: Dict) -> Dict:
    """
    根据用户偏好动态计算房源评分
    """
    districts_data = load_districts_data()
    district_info = districts_data.get('districts', {}).get(listing.get('district'), {})
    
    # 获取用户自定义权重，或使用默认权重
    weights = user_preferences.get('weights', {
        'price': 0.30,
        'location': 0.25,
        'facility': 0.20,
        'safety': 0.15,
        'distance': 0.10
    })
    
    scores = {}
    
    # 价格评分（越低越好）
    price = listing.get('price', 0)
    max_price = user_preferences.get('max_price', 1000)
    if price <= max_price * 0.6:
        scores['price_score'] = 10
    elif price <= max_price * 0.75:
        scores['price_score'] = 8
    elif price <= max_price * 0.9:
        scores['price_score'] = 6
    elif price <= max_price:
        scores['price_score'] = 4
    else:
        scores['price_score'] = 2
    
    # 安全评分（使用区域数据）
    safety_score = district_info.get('safety_score', 6.0)
    scores['safety_score'] = safety_score
    
    # 距离评分（基于目标学校）
    distance_km = district_info.get('distance_polito_km', 5)
    if distance_km <= 1:
        scores['distance_score'] = 10
    elif distance_km <= 2:
        scores['distance_score'] = 8
    elif distance_km <= 3:
        scores['distance_score'] = 6
    elif distance_km <= 5:
        scores['distance_score'] = 4
    else:
        scores['distance_score'] = 2
    
    # 位置评分（综合安全和距离）
    scores['location_score'] = (safety_score * 0.5 + scores['distance_score'] * 0.5)
    
    # 设施评分
    facility_score = 5
    if listing.get('furnished'):
        facility_score += 2
    if listing.get('has_ac'):
        facility_score += 1
    if listing.get('has_elevator'):
        facility_score += 0.5
    if listing.get('heating') == 'independent':
        facility_score += 1.5
    scores['facility_score'] = min(10, facility_score)
    
    # 房型匹配评分
    preferred_type = user_preferences.get('room_type')
    if preferred_type:
        if listing.get('type') == preferred_type:
            scores['type_match_score'] = 10
        elif listing.get('type') == 'room' and preferred_type == 'studio':
            scores['type_match_score'] = 6  # 合租单间也可以接受
        else:
            scores['type_match_score'] = 4
    else:
        scores['type_match_score'] = 7  # 没有偏好
    
    # 综合评分
    overall_score = (
        scores['price_score'] * weights.get('price', 0.30) +
        scores['safety_score'] * weights.get('safety', 0.15) +
        scores['distance_score'] * weights.get('distance', 0.10) +
        scores['location_score'] * weights.get('location', 0.25) +
        scores['facility_score'] * weights.get('facility', 0.20)
    )
    
    # 房型匹配加成
    if scores.get('type_match_score', 0) >= 8:
        overall_score *= 1.1
    elif scores.get('type_match_score', 0) <= 5:
        overall_score *= 0.9
    
    scores['overall_score'] = min(10, overall_score)
    
    listing.update(scores)
    return listing


def generate_recommendation_reason(listing: Dict, user_preferences: Dict) -> str:
    """
    生成推荐理由
    """
    districts_data = load_districts_data()
    district_info = districts_data.get('districts', {}).get(listing.get('district'), {})
    reasons = []
    
    # 价格优势
    max_price = user_preferences.get('max_price', 0)
    price = listing.get('price', 0)
    if max_price and price <= max_price * 0.75:
        reasons.append(f"价格低于预算{((max_price - price) / max_price * 100):.0f}%")
    elif max_price and price <= max_price:
        reasons.append(f"价格在预算内")
    
    # 安全性
    safety_score = district_info.get('safety_score', 0)
    if safety_score >= 8:
        reasons.append(f"安全区域（评分{safety_score}/10）")
    elif safety_score >= 7:
        reasons.append(f"较安全（评分{safety_score}/10）")
    
    # 距离学校
    distance_km = district_info.get('distance_polito_km', 0)
    bike_time = district_info.get('bike_time_polito_min', 0)
    if distance_km <= 1.5:
        reasons.append(f"距离学校{distance_km}km，自行车{bike_time}分钟")
    
    # 设施
    if listing.get('furnished'):
        reasons.append("带家具")
    if listing.get('heating') == 'independent':
        reasons.append("独立供暖")
    elif listing.get('heating') == 'centralized':
        reasons.append("集中供暖")
    
    # 区域特点
    characteristics = district_info.get('characteristics', '')
    if characteristics:
        reasons.append(characteristics)
    
    return '；'.join(reasons) if reasons else "综合条件符合需求"
