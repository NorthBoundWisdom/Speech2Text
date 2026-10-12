# 隐私与数据

## 本地处理

本地 ASR 读取音视频和模型，生成转录、字幕、QA 与日志。这个阶段不上传音频。链接导入、RSS 刷新和手动模型下载仍需要访问相应来源。

默认运行数据在 `~/Documents/SpeechToTextData/`，其中 `model/` 保存模型，`materials/` 保存音视频素材，`work/` 保存过程文件，`cache/` 保存日志和工具缓存。JSON 与 Markdown 资料库可以使用本地目录，也可以选择 iCloud Drive。

## 你选择的联网流程

| 功能 | 哪些数据离开本机 |
| --- | --- |
| iCloud Drive 资料库 | 按系统同步策略上传节目 JSON、转录、摘要与状态文件 |
| MCP / Codex 总结 | Agent 读取的转录、QA 与摘要进入客户端会话 |
| 可选云 API 总结 | 文本与相关文本元信息发送至你配置的 API；此路径不发送原始音视频或模型 |

MCP 服务本身不调用模型 API；客户端模型是否本地运行由客户端决定。

## 凭据与日志

macOS 使用 Keychain，Windows CLI 使用 Credential Manager，iOS 使用设备 Keychain 存储云凭据。公开配置不返回明文 Key，也没有明文凭据存储的静默替代方式。

日志会脱敏常见密钥与 bearer token，但不能识别任意文本中的所有私人信息。分享诊断、转录或截图前，请检查其实际内容。

官网不配置访问统计、不加载远程字体。搜索索引与静态资源随站点部署；页面请求仍由 GitHub Pages 托管服务处理。点击 GitHub 或模型下载链接时适用目标服务的数据政策。

完整产品数据边界见[源码隐私说明](https://github.com/NorthBoundWisdom/sonafolio/blob/main/doc/PRIVACY.md)。
