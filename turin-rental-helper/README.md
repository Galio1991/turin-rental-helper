# Turin Rental Helper Core

本目录包含 Turin Rental Helper 的 Skill、Python 决策引擎、命令行入口和测试。

## 运行环境

- Python 3.10+
- 核心无第三方运行时依赖
- 支持以 Skill 方式调用，也支持直接使用 JSON CLI 或 Python API

## 命令行使用

```bash
python3 scripts/rank_listings.py \
  --listings tests/fixtures/listings.json \
  --preferences tests/fixtures/preferences.json \
  --output /tmp/recommendations.json \
  --limit 10
```

参数：

| 参数 | 必需 | 说明 |
|---|---|---|
| `--listings` | 是 | UTF-8 JSON 数组，遵循房源数据规范 |
| `--preferences` | 是 | UTF-8 JSON 对象，包含约束、偏好和权重 |
| `--output` | 否 | 输出文件；省略时写入标准输出 |
| `--limit` | 否 | 返回数量，默认 10 |

无效输入记录不会导致整批任务中断，会出现在结果的 `invalid` 中。明确违反硬约束的房源会出现在 `rejected` 中；规范化 URL 相同的房源会出现在 `duplicates` 中。

## Python API

将 `scripts` 加入 Python 模块搜索路径后，可以直接调用核心管线：

```python
from rental_helper import recommend

result = recommend(
    raw_listings=[
        {
            "id": "source:123",
            "source": "source",
            "title": "Example studio",
            "url": "https://example.test/123",
            "base_rent": 560,
            "mandatory_expenses": 70,
            "estimated_utilities": 45,
            "property_type": "studio",
            "commute_minutes": 18,
        }
    ],
    raw_preferences={
        "max_total_monthly": 750,
        "max_commute_minutes": 35,
        "property_types": ["studio"],
    },
    limit=5,
)

payload = result.to_dict()
```

公开入口：

- `Listing.from_dict(...)`：校验并建立规范房源；
- `Preferences.from_dict(...)`：校验约束并归一化权重；
- `recommend(...)`：执行校验、去重、筛选、评分和多样化；
- `RecommendationResult.to_dict()`：生成可序列化结果。

## 已获取文本的解析

`IdealistaMarkdownAdapter` 只解析已经取得的 Markdown 文本，不发起网络请求：

```python
from rental_helper.adapters import IdealistaMarkdownAdapter

listings = IdealistaMarkdownAdapter().parse(markdown_text)
```

页面未出现的设施字段保持 `None`。为没有明确写出的内容猜测 `True` 或 `False` 会破坏后续约束和置信度逻辑。

## 数据与评分文档

- [房源数据规范](references/listing-schema.md)：字段类型、费用语义、证据要求和偏好格式。
- [推荐方法](references/ranking-method.md)：约束、连续效用、置信度、Pareto 和分数解释。
- [架构说明](docs/architecture.md)：模块边界、扩展点与工程不变量。
- [v2 迁移指南](docs/migration-v2.md)：旧字段和旧接口迁移方式。

## 开发与验证

运行完整测试：

```bash
python3 -m unittest discover -s tests -v
```

运行端到端样例：

```bash
python3 scripts/rank_listings.py \
  --listings tests/fixtures/listings.json \
  --preferences tests/fixtures/preferences.json \
  --limit 2
```

修改算法时必须验证以下性质：

1. 成本和通勤效用具有正确的单调性；
2. 房源原始分数不依赖候选集合；
3. 缺失值不会被转换成虚构的普通分数；
4. 未带来源、日期和粒度的安全指标不会参与评分；
5. 展示层多样化可以改变顺序，但不能修改原始分数。

## 安装为 Skill

默认安装到 `~/.claude/skills/turin-rental-helper`：

```bash
./install.sh
```

也可以指定其他目标目录：

```bash
./install.sh /path/to/skills/turin-rental-helper
```

安装器不会覆盖已有路径。如果目标已存在，应先备份或检查差异，再明确处理旧版本。

## 兼容性

`scripts/comparator.py` 和 `scripts/scraper.py` 保留旧项目常用函数名，但内部已委托给 v2 模型与评分逻辑。新代码不应继续依赖旧版 `price_score`、`location_score` 或 `closeness` 语义。

旧版 `assets/data/turin-districts.json` 仅保留用于迁移和核验，不进入默认推荐流程。
