# QA 与修复

自动转录可能出现漏句、重复、术语或时间戳问题。SonaFolio 保存 QA、修正规则记录与审阅线索，方便你判断哪些内容需要回听。

```bash
atot exec qa path/to/work-dir
atot exec repair path/to/work-dir --plan-only
```

先查看 `qa.json`、`review.json`、`entity_consistency.json` 和修复计划。确认需要局部替换时再执行：

```bash
atot exec repair path/to/work-dir
```

修复需要对应本地后端与模型，不应被当作纯文本润色。自动修正记录在 `corrections.json`；需要人工确认的术语保留为审阅项，不自动推广为全局替换。

QA 通过说明通过了程序的指标检查，并不代表文本逐字准确。研究、引用或重要判断应结合原始音频核实。

候选 ASR 后端只有通过相同质量门禁和语义审阅才会晋升。实验记录描述当时测量结果，不能当作当前支持承诺。

[质量规则与研究文档](https://github.com/NorthBoundWisdom/sonafolio/blob/main/doc/QUALITY_LOOP.md)
