# 房源数据规范

## 必需字段

| 字段 | 类型 | 含义 |
|---|---|---|
| `id` | string | 来源内稳定 ID；没有时可使用规范化 URL |
| `source` | string | 数据来源，例如 `idealista` |
| `title` | string | 房源标题 |
| `url` | string | 原始页面；查询参数会在去重时移除 |
| `base_rent` | number/null | 基础月租；未知时为 `null` |

`id/source/title/url` 是身份和溯源字段。解析器至少应获得 ID 或 URL；无效记录会进入 `invalid`，不会被静默打分。

## 费用字段

- `mandatory_expenses`：每月固定物业或公摊费用。
- `estimated_utilities`：预估水、电、燃气、供暖等月均费用。
- `deposit`：一次性押金，不加入月度成本。
- `known_monthly_cost` 由核心计算，不应在输入中手工覆盖。

只要固定费用或水电暖未知，月度总额就应描述为“已知费用”，同时降低费用置信度。

## 房源与位置字段

- `area_sqm`、`rooms`、`property_type`
- `district`、`address`
- `commute_minutes`：从具体地址到用户目标地点的预计门到门时间。
- `furnished`、`has_ac`、`has_elevator`：必须使用布尔值或 `null`。
- `heating`：推荐使用 `independent`、`centralized` 或 `null`。

## 证据字段

- `observed_at`：ISO 日期，例如 `2026-09-29`。
- `extraction_confidence`：整条记录的 0–1 置信度。
- `field_confidence`：字段级 0–1 置信度映射。
- `safety_score`：可选的 0–10 指标。还必须提供 `safety_source`、`safety_observed_at` 和 `safety_granularity` 才会参与评分；核心不会从区域名称自动生成该值。

## 偏好字段

硬约束包括 `max_total_monthly`、`max_base_rent`、`max_commute_minutes`、`min_area_sqm`、`property_types` 以及值为 `true` 的设施要求。

`unknown_hard_policy`：

- `warn`：字段未知时保留候选并输出警告；默认值。
- `reject`：字段未知时拒绝候选，适合用户明确要求严格筛选。

`weights` 支持 `cost`、`commute`、`space`、`amenities`、`safety`。输入权重会自动归一化；旧名称 `price`、`distance`、`facility` 可兼容映射。
