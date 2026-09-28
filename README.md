# Turin Rental Helper

面向都灵留学生的租房决策引擎与 Agent Skill。

Turin Rental Helper 不试图用一个含糊的“综合分”代替判断。它把房源信息整理成可核查的数据，明确区分硬约束、个人偏好和未知信息，再给出带证据覆盖率、主要取舍和待核实事项的推荐结果。

> 当前版本为 v2 核心重构版。项目处理用户提供或经授权工具取得的房源内容，不内置绕过网站限制的自动爬虫。

## 为什么重构

传统的租房打分脚本常见三个问题：只比较页面标价、把缺失字段当成普通值，以及让候选集合本身改变评分结果。v2 针对这些问题重新设计：

- 比较“已知月度成本”，分别记录基础租金、固定费用和预估水电暖；
- 使用 `true / false / null` 保存设施状态，不把“页面没写”解释为“没有”；
- 先执行预算、房型、通勤等硬约束，再计算软偏好效用；
- 每套房源独立评分，新增其他候选不会改变它自身的原始分数；
- 同时报告评分和资料覆盖率，信息残缺的房源不会伪装成确定答案；
- 不根据区域名称或人口构成自动判断风险，安全指标必须具备来源、日期和地理粒度。

## 能力边界

| 能力 | 当前状态 | 说明 |
|---|---|---|
| 结构化房源校验 | 可用 | 无效记录单独报告，不静默进入排名 |
| 费用、通勤、面积和设施评分 | 可用 | 连续效用函数，权重可配置 |
| 硬约束与未知值策略 | 可用 | 未知字段可选择警告保留或严格拒绝 |
| URL 去重 | 可用 | 移除追踪参数后识别同一房源 |
| Pareto 与结果多样化 | 可用 | 标记未被全面支配的房源，减少单一来源垄断结果 |
| Idealista Markdown 解析 | 可用 | 解析已获取的页面文本，不执行网络请求 |
| 地址级路线计算 | 由调用方提供 | 核心接收 `commute_minutes` |
| 实时库存抓取 | 不内置 | 应由遵守来源规则的外部适配器完成 |

## 决策流程

```text
用户需求
   │
   ├─ 硬约束：总预算、房型、最长通勤、必需设施
   └─ 软偏好：成本、通勤、面积、设施、安全证据权重
   │
房源输入 ─→ 校验 ─→ 规范化 ─→ 去重 ─→ 硬约束检查
                                         │
                                         ├─ 拒绝项及原因
                                         └─ 候选房源
                                              │
                         可信度感知效用评分 ─→ Pareto 标记 ─→ 多样化推荐
                                              │
                         得分、覆盖率、取舍、警告、待核实项
```

更完整的模块关系和扩展约束见 [架构说明](turin-rental-helper/docs/architecture.md)。

## 快速开始

环境要求：Python 3.10+。核心仅使用标准库。

```bash
git clone https://github.com/Galio1991/turin-rental-helper.git
cd turin-rental-helper/turin-rental-helper

python3 -m unittest discover -s tests -v

python3 scripts/rank_listings.py \
  --listings tests/fixtures/listings.json \
  --preferences tests/fixtures/preferences.json \
  --limit 5
```

也可以安装为 Skill。默认目标为 Claude Code 的 Skill 目录；其他 Agent 环境可以显式传入目标路径：

```bash
./install.sh

# 示例：安装到其他 Skill 目录
./install.sh /path/to/skills/turin-rental-helper
```

安装器不会覆盖已有目录，升级时需要先明确处理旧版本，避免意外删除本地修改。

## 输入示例

房源列表：

```json
[
  {
    "id": "idealista:123456",
    "source": "idealista",
    "title": "Monolocale arredato in Cenisia",
    "url": "https://www.idealista.it/immobile/123456/",
    "base_rent": 560,
    "mandatory_expenses": 70,
    "estimated_utilities": 45,
    "deposit": 1120,
    "area_sqm": 28,
    "property_type": "studio",
    "district": "Cenisia",
    "commute_minutes": 18,
    "furnished": true,
    "observed_at": "2026-09-29",
    "extraction_confidence": 0.95
  }
]
```

用户偏好：

```json
{
  "max_total_monthly": 750,
  "max_commute_minutes": 35,
  "target_commute_minutes": 20,
  "min_area_sqm": 16,
  "property_types": ["studio", "room"],
  "furnished": true,
  "unknown_hard_policy": "warn",
  "weights": {
    "cost": 0.45,
    "commute": 0.30,
    "space": 0.10,
    "amenities": 0.15,
    "safety": 0
  }
}
```

输出中每套房源包含：

- `score`：当前偏好与当前证据下的 0–100 适配分；
- `coverage`：加权后的资料覆盖率；
- `pareto_optimal`：是否位于当前候选集的 Pareto 前沿；
- `features`：每个维度的效用、置信度和解释；
- `warnings`：费用或设施等未确认信息；
- `tradeoffs`：已知但表现较弱的主要取舍。

完整字段定义见 [房源数据规范](turin-rental-helper/references/listing-schema.md)，评分语义见 [推荐方法](turin-rental-helper/references/ranking-method.md)。

## 项目结构

```text
.
├── README.md
├── CLAUDE.md                         # 仓库开发约束
└── turin-rental-helper/
    ├── SKILL.md                      # Agent Skill 入口
    ├── README.md                     # 运行与开发手册
    ├── docs/
    │   ├── architecture.md           # 架构与扩展指南
    │   └── migration-v2.md           # v1 到 v2 迁移说明
    ├── references/
    │   ├── listing-schema.md         # 输入契约
    │   └── ranking-method.md         # 算法与解释边界
    ├── scripts/
    │   ├── rank_listings.py          # CLI
    │   ├── comparator.py             # v1 兼容入口
    │   ├── scraper.py                # v1 文本解析兼容入口
    │   └── rental_helper/            # v2 核心包
    └── tests/                         # 行为、不变量与端到端测试
```

## 设计质量

测试关注可观察行为，而不是实现细节。目前覆盖：

- 其他条件相同时，更低成本不会得到更低分；
- 其他条件相同时，更短通勤不会得到更低分；
- 某套房源的原始分数不随候选集合变化；
- 未知费用产生警告，已知超预算直接拒绝；
- 未提供证据元数据的安全分不参与评分；
- URL 追踪参数不会制造重复房源；
- 旧版模块仍可导入和调用。

## 版本迁移

v2 不再使用旧版 AHP/TOPSIS 名称或区域硬编码排除规则。旧调用入口仍然保留，但建议新集成直接使用 `rental_helper.recommend` 或 CLI。字段映射和行为差异见 [v2 迁移指南](turin-rental-helper/docs/migration-v2.md)。

## 路线图

后续扩展优先级：

1. 增加独立的 Immobiliare 等来源适配器及固定解析样本；
2. 接入可替换的地理编码与公共交通路线提供方；
3. 增加合同期限、能源等级和一次性入住成本模型；
4. 在获得真实用户选择数据后，再评估是否需要学习排序，而非提前引入不可解释模型。

## License

[MIT](LICENSE)
