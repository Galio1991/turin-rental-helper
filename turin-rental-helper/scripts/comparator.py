#!/usr/bin/env python3
"""
房源对比推荐模块
使用AHP-TOPSIS方法对房源进行排序推荐
"""

import numpy as np
from typing import Dict, List, Optional


class ListingComparator:
    """房源对比器"""

    def __init__(self, weights: Optional[Dict[str, float]] = None):
        """
        Args:
            weights: 指标权重 {'price': 0.4, 'location': 0.3, 'facility': 0.2, 'safety': 0.1}
        """
        self.weights = weights or {
            'price': 0.35,
            'location': 0.30,
            'facility': 0.20,
            'safety': 0.15
        }
        self.criteria = list(self.weights.keys())
        # 价格越低越好，其他越高越好
        self.impacts = ['-', '+', '+', '+']

    def calculate_scores(self, listings: List[Dict]) -> List[Dict]:
        """
        计算每个房源的综合得分

        Args:
            listings: 房源列表，每个房源包含评分信息

        Returns:
            添加了综合得分的房源列表
        """
        if not listings:
            return []

        # 提取评分矩阵
        scores = []
        for listing in listings:
            score = [
                listing.get('price_score', 5),
                listing.get('location_score', 5),
                listing.get('facility_score', 5),
                listing.get('safety_score', 5)
            ]
            scores.append(score)

        matrix = np.array(scores)

        # 标准化
        norm = np.sqrt((matrix ** 2).sum(axis=0))
        norm_matrix = matrix / norm

        # 加权
        weight_vector = np.array([self.weights[c] for c in self.criteria])
        weighted_matrix = norm_matrix * weight_vector

        # 理想解
        ideal_best = np.zeros(len(self.criteria))
        ideal_worst = np.zeros(len(self.criteria))

        for i in range(len(self.criteria)):
            if self.impacts[i] == '+':
                ideal_best[i] = weighted_matrix[:, i].max()
                ideal_worst[i] = weighted_matrix[:, i].min()
            else:
                ideal_best[i] = weighted_matrix[:, i].min()
                ideal_worst[i] = weighted_matrix[:, i].max()

        # 距离
        dist_best = np.sqrt(((weighted_matrix - ideal_best) ** 2).sum(axis=1))
        dist_worst = np.sqrt(((weighted_matrix - ideal_worst) ** 2).sum(axis=1))

        # 接近度
        closeness = dist_worst / (dist_best + dist_worst)

        # 添加得分到房源
        for i, listing in enumerate(listings):
            listing['closeness'] = float(closeness[i])

        # 按接近度排序
        listings.sort(key=lambda x: x.get('closeness', 0), reverse=True)

        return listings


def rank_listings(listings: List[Dict], weights: Optional[Dict] = None) -> List[Dict]:
    """
    对房源进行排名

    Args:
        listings: 房源列表
        weights: 权重配置

    Returns:
        排名后的房源列表
    """
    comparator = ListingComparator(weights)
    return comparator.calculate_scores(listings)
