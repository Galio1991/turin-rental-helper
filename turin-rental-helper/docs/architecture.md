# 架构说明

## 目标

核心引擎只负责可重复的决策计算：接收规范房源和用户偏好，返回可解释结果。网页访问、地理编码和地图展示属于外部能力，通过明确字段与核心连接。

这种边界让同一套算法可以用于 Agent Skill、命令行批处理或未来的 Web 服务，而不会把网站解析、业务规则和展示逻辑耦合在一个脚本里。

## 模块关系

```text
Source text / canonical JSON
          │
          ▼
 adapters.py ──────── source-specific parsing
          │
          ▼
 models.py ───────── validation and canonical types
          │
          ▼
 ingestion.py ────── normalization and de-duplication
          │
          ▼
 ranking.py ──────── constraints, utility, confidence, Pareto, diversity
          │
          ▼
 pipeline.py ─────── orchestration and structured result
          │
          ├───────── rank_listings.py CLI
          └───────── Agent Skill / Python caller
```

## 模块职责

### `models.py`

定义 `Listing`、`Preferences`、`FeatureScore` 和 `RankedListing`。模型层完成类型校验、旧字段映射、权重归一化和派生的已知月度成本计算。

模型不访问网络，也不读取区域数据。这样可以保证相同输入产生相同的规范对象。

### `adapters.py`

每个来源使用独立适配器。适配器只处理来源文本到 `Listing` 的转换，并保存字段置信度；不得执行排名，也不得把未出现的字段推断为否。

新增适配器时应：

1. 使用固定输入样本编写解析测试；
2. 为来源内 ID 生成稳定的全局 ID；
3. 保留原始 URL 和抓取/观察日期；
4. 对推断字段设置低于直接读取字段的置信度；
5. 避免把多个来源继续堆进同一组正则表达式。

### `ingestion.py`

处理与来源无关的文本规范化和 URL 去重。URL 查询参数不会作为房源身份的一部分，避免广告追踪参数制造重复记录。

如果未来需要跨网站识别同一房源，应新增独立的实体匹配阶段，并输出匹配概率，不能仅依赖标题模糊匹配后直接删除。

### `ranking.py`

由五个部分组成：

1. 硬约束判断；
2. 各维度的连续效用函数；
3. 置信度折算和资料覆盖率；
4. Pareto 前沿标记；
5. 面向展示的轻量多样化。

原始适配分与候选集合无关。Pareto 和多样化使用候选集合，但只能影响标签和展示顺序，不能回写某套房源的原始分数。

### `pipeline.py`

管线负责批量容错。单条记录无效时进入 `invalid`；重复项进入 `duplicates`；违反硬约束的房源进入 `rejected`；其余记录进入 `recommendations`。

## 数据可信度

评分结果同时包含 `score` 和 `coverage`：

- `score` 回答“在已配置偏好下，这套房源的证据表现如何”；
- `coverage` 回答“这些证据覆盖了多少加权决策维度”。

两者不能互相替代。高分低覆盖率意味着值得补充资料，不意味着已经确认优质。

安全指标是特殊证据。只有同时存在 `safety_source`、`safety_observed_at` 和 `safety_granularity` 时，`safety_score` 才会进入计算。

## 稳定性要求

算法变更应保持：

- 确定性：同一输入与配置得到同一原始分数；
- 单调性：其他条件相同，更低费用和更短通勤不应降低效用；
- 候选独立性：其他房源的加入或移除不改变当前房源原始分数；
- 可追溯性：每个分数维度提供人类可读解释；
- 保守缺失值：未知字段不能获得与高质量已知证据相同的效果。

## 未来服务化

如果以后增加 API 或数据库，建议让服务层只完成认证、存储和调用编排，继续复用当前纯函数式核心。外部路线提供方和实时房源来源应通过接口注入，避免在领域模型中绑定特定供应商。
