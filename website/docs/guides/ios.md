# iPhone 与 iPad 阅读端

当前 iOS/iPadOS 客户端是资料库阅读与订阅管理端，不运行本机 ASR，也不下载录音用于处理。先在受支持的电脑完成转写，再共享阅读文档。

## 分发与要求

要求 iOS/iPadOS 17+。目前没有 App Store、TestFlight 或自动 IPA 分发，使用源码构建。Xcode 模拟器构建用于验证；安装真机还需要自己的开发签名与设备配置。

在仓库根目录：

```bash
python3 configs/setup_local_app.py
python3 configs/ios_workflow.py build --platform ios --scheme Audio2Text-iOS --configuration debug
```

进一步构建信息见[开发说明](../development.md)。不要把 macOS 的 ad-hoc DMG 当成 iOS 安装包。

## 选择已有资料库

1. 在 Mac 的 Library 设置确认 iCloud 权威位置。
2. 等待系统把资料库文档同步到 iCloud Drive。
3. 在 iOS 设置通过 Files 选择已有 `Audio2Text` 或 `Audio2TextLibrary` 文件夹，授予文件访问权限。
4. 刷新阅读列表，检查一份已经有转写的单集。
5. 若文件尚未下载，先等待 Files/iCloud 使其可用。

选的是现有库，不能仅新建一个同名空目录就得到 Mac 内容。默认兼容路径与名称见[存储说明](storage.md)。

## 可用操作

阅读转写、已有总结与来源，管理阅读、收藏、归档与分组状态，以及订阅元数据。更新会通过资料库文件和系统同步传播；媒体与模型仍留在处理电脑。

没有文档的元数据条目会缺少阅读内容。这不表示手机应自动启动转写；应回到电脑下载/处理，再等待文档同步。

## 同步不一致时

比较两端实际选择的库目录和文件，而不只是 App 显示的名字。检查过滤器、文件下载状态与 Files 授权；重新选择文件夹后再刷新。避免同步中并行移动/删除整个库。

iCloud 是系统级文件同步，不提供本项目承诺的固定时延，也不能代替独立备份。

[同步排查 →](troubleshooting.md#the-library-is-empty-or-different-on-another-device) · [备份 →](storage.md)
