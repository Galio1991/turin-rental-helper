# v2 迁移指南

v2 重写了推荐核心，但保留 `scripts/comparator.py` 和 `scripts/scraper.py` 作为过渡入口。

## 行为变化

| v1 | v2 |
|---|---|
| 固定的区域安全排除名单 | 不按区域名称自动排除；仅使用带证据元数据的指标 |
| `price_score` 再作为成本型 TOPSIS 指标 | 直接基于费用与用户预算计算连续效用 |
| 缺失字段使用默认中间分 | 缺失字段保持未知，并降低覆盖率 |
| 区域级理工距离 | 优先接收具体地址的 `commute_minutes` |
| 房型匹配乘以固定加成 | 房型作为明确硬约束或由调用方调整偏好 |
| 排名依赖当前候选矩阵 | 每套房源原始分数独立计算 |
| NumPy 运行时依赖 | Python 3.10+ 标准库实现 |

## 房源字段映射

| 旧字段 | v2 字段 | 备注 |
|---|---|---|
| `price` | `base_rent` | 兼容读取，但新数据应使用新字段 |
| `area` | `area_sqm` | 兼容读取 |
| `type` | `property_type` | 兼容读取 |
| `price_score` | 删除 | 由预算和费用计算 |
| `distance_score` | 删除 | 使用 `commute_minutes` |
| `facility_score` | 删除 | 使用设施三态字段 |
| `location_score` | 删除 | 不再重复计入距离与安全 |
| `overall_score` | `score` | v2 输出范围为 0–100 |
| `closeness` | 删除 | 兼容层暂以 `score / 100` 返回 |

## 偏好字段映射

| 旧字段 | v2 字段 |
|---|---|
| `max_price` | `max_total_monthly` |
| `room_type` | `property_types` 数组 |
| 权重 `price` | `cost` |
| 权重 `distance` | `commute` |
| 权重 `facility` | `amenities` |

旧权重 `location` 在兼容解析时平均分配给 `commute` 和 `safety`。新配置应直接表达真实取舍，避免继续使用含义重叠的 `location`。

## 推荐迁移方式

旧代码：

```python
from comparator import rank_listings

ranked = rank_listings(listings, weights)
```

新代码：

```python
from rental_helper import recommend

result = recommend(listings, preferences, limit=10)
ranked = result.ranked
```

调用方应分别处理 `invalid`、`duplicates` 和 `rejected`，而不是只读取最终推荐数组。这些信息是解释数据质量和筛选结果的一部分。

## 区域数据

`assets/data/turin-districts.json` 已标记为 `legacy_unverified`，默认排名器不会加载它。若要重新启用其中某类信息，应先补充权威来源、采集日期、地理粒度和更新机制，再通过显式的特征丰富阶段写入房源记录。
