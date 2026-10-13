# QA、核对与修复

ASR 可能漏句、重复、误认术语或错配时间。SonaFolio 保留 QA、纠正与审阅证据，帮助决定哪里值得复听。中文主路径经过验证，也不代表每个节目都逐字准确。

## 先读取证据

使用转写报告的工作目录：

```bash
atot exec qa path/to/work-dir --json
atot exec repair path/to/work-dir --plan-only --json
```

| 证据 | 看什么 |
| --- | --- |
| qa.json | 状态、问题类型及时间窗口 |
| corrections.json | 程序做过哪些确定性修改 |
| review.json | 不确定词语与候选审阅 |
| entity_consistency.json | 人名/实体不一致 |
| 修复计划 | 哪些音频窗口值得重跑 |

QA 失败是核对信号，不等于所有文本不可读；通过也不是准确率证明。重点核对数字、专有名词、结论、引用，以及异常长空白或重复段。

## 先计划，再执行

`--plan-only` 生成候选窗口而不执行重识别。查看时间范围、理由和对应音频，确认确有必要后：

```bash
atot exec repair path/to/work-dir --json
```

修复需要匹配的本地后端与模型，它是对局部音频重新识别，不是纯文本润色。会修改相关工作产物，需要保留旧版本时先备份；完成后重新核对文本与 QA。

## 术语与规则

可用自定义 glossary/prompt 或共享 rule pack 提供真正的背景。确定性纠正写入 corrections.json；不确定术语应保持审阅状态，不能从一次错误结果推导全局替换。

总结与标题正确不证明 ASR 正确，也不能用一份流畅总结覆盖原文错误。候选后端与模型需通过同等质量门和语义审查；历史实验不能证明当前版本或所有语言已经得到验证。

[转写操作 →](transcription.md) · [故障排查 →](troubleshooting.md)
