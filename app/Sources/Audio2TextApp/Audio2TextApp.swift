import AppKit
import Darwin
import SwiftUI

final class AppDelegate: NSObject, NSApplicationDelegate {
    private var instanceLock: ApplicationInstanceLock?

    func applicationWillFinishLaunching(_: Notification) {
        do {
            if let lock = try ApplicationInstanceLock.acquire() {
                instanceLock = lock
                return
            }
            activateExistingApplication()
            NSApp.terminate(nil)
        } catch {
            AppLogger.shared.log(.error, category: "app", event: "instance_lock_failed", message: error.localizedDescription)
        }
    }

    func applicationDidFinishLaunching(_: Notification) {
        NSApp.setActivationPolicy(.regular)
        NSApp.applicationIconImage = AppIconFactory.image()
        NSApp.activate(ignoringOtherApps: true)
    }

    func applicationWillTerminate(_: Notification) {
        AppLogger.shared.log(.info, category: "app", event: "app_exit", message: "SonaFolio app is terminating")
    }

    private func activateExistingApplication() {
        guard let bundleIdentifier = Bundle.main.bundleIdentifier else {
            return
        }
        let currentProcessIdentifier = ProcessInfo.processInfo.processIdentifier
        let existingApplication = NSRunningApplication
            .runningApplications(withBundleIdentifier: bundleIdentifier)
            .first { $0.processIdentifier != currentProcessIdentifier }
        existingApplication?.activate(options: [.activateAllWindows])
    }
}

@main
struct Audio2TextApp: App {
    @NSApplicationDelegateAdaptor(AppDelegate.self) private var appDelegate
    @StateObject private var store = AppStore.makeLive()

    init() {
        if let exitCode = Audio2TextCliLauncher.runIfRequested() {
            Darwin.exit(exitCode)
        }
    }

    var body: some Scene {
        WindowGroup("SonaFolio") {
            ContentView(store: store)
                .frame(minWidth: 980, minHeight: 680)
                .onAppear {
                    NSApp.setActivationPolicy(.regular)
                    NSApp.activate(ignoringOtherApps: true)
                }
        }
        .windowStyle(.titleBar)
        .commands {
            Audio2TextCommands(store: store)
        }
    }
}

struct Audio2TextCommands: Commands {
    @ObservedObject var store: AppStore

    var body: some Commands {
        CommandGroup(replacing: .appSettings) {
            Button("Settings...") {
                store.showSettings()
            }
            .keyboardShortcut(",", modifiers: .command)
        }

        CommandGroup(replacing: .newItem) {
            Button("New Item") {
                store.showImportPanel()
            }
            .keyboardShortcut("n", modifiers: .command)

            Button("New Group") {
                store.isNewGroupPanelPresented = true
            }
            .keyboardShortcut("n", modifiers: [.command, .shift])

            Button("Generate SRT...") {
                store.showSRTExportPanel()
            }
            .keyboardShortcut("s", modifiers: [.command, .shift])
        }

        CommandMenu("Process") {
            Button("Refresh") {
                store.job.refresh()
            }
            .keyboardShortcut("r", modifiers: .command)

            Button("Refresh Library") {
                store.job.refreshLibraryNow()
            }
            .keyboardShortcut("i", modifiers: [.command, .shift])

            Divider()

            Button(ProcessingWorkflow.transcribeAndSummarize.actionTitle(isCloudConfigured: store.job.isCloudSummaryConfigured)) {
                if let item = store.selectedLibraryItem {
                    store.job.processLibraryItem(item, workflow: .transcribeAndSummarize)
                }
            }
            .disabled(!store.job.canProcessLibraryItem(store.selectedLibraryItem, workflow: .transcribeAndSummarize))

            Button(ProcessingWorkflow.localOnly.actionTitle()) {
                if let item = store.selectedLibraryItem {
                    store.job.processLibraryItem(item, workflow: .localOnly)
                }
            }
            .keyboardShortcut(.return, modifiers: .command)
            .disabled(!store.job.canProcessLibraryItem(store.selectedLibraryItem, workflow: .localOnly))

            Button(ProcessingWorkflow.transcribeAndSummarize.actionTitle(reprocess: true, isCloudConfigured: store.job.isCloudSummaryConfigured)) {
                if let item = store.selectedLibraryItem {
                    store.job.processLibraryItem(item, reprocess: true, workflow: .transcribeAndSummarize)
                }
            }
            .disabled(!store.job.canProcessLibraryItem(store.selectedLibraryItem, reprocess: true, workflow: .transcribeAndSummarize))

            Button(ProcessingWorkflow.localOnly.actionTitle(reprocess: true)) {
                if let item = store.selectedLibraryItem {
                    store.job.processLibraryItem(item, reprocess: true, workflow: .localOnly)
                }
            }
            .keyboardShortcut(.return, modifiers: [.command, .shift])
            .disabled(!store.job.canProcessLibraryItem(store.selectedLibraryItem, reprocess: true, workflow: .localOnly))

            Button("复制 Codex 总结回写指令") {
                if let item = store.selectedLibraryItem {
                    let prompt = """
                    使用已连接的 SonaFolio MCP 为 episode_id="\(item.id)" 生成中文 Markdown 总结并回写。
                    先 get_episode 获取版本和 QA 信息，再通过 read_document 分页读完全部转录，保留有用的时间标记。
                    使用你当前的模型总结，不调用 SonaFolio 云 API。
                    write_summary 时传入 transcript_sha256 和 summary_sha256，generator 填 Codex。
                    如果已有非空总结，先确认用户是否要求重新生成；不要自行设置 overwrite=true。
                    """
                    NSPasteboard.general.clearContents()
                    NSPasteboard.general.setString(prompt, forType: .string)
                }
            }
            .disabled(store.selectedLibraryItem?.documentsURL == nil || !store.job.canGenerateSummary(for: store.selectedLibraryItem))

            Button("云 API 重新生成总结") {
                if let item = store.selectedLibraryItem {
                    store.job.generateSummary(for: item)
                }
            }
            .keyboardShortcut("s", modifiers: [.command, .option])
            .disabled(!store.job.isCloudSummaryConfigured || !store.job.canGenerateSummary(for: store.selectedLibraryItem))

            Button("Restore Missing Audio") {
                if let item = store.selectedLibraryItem {
                    store.job.restoreAudio(for: item)
                }
            }
            .keyboardShortcut("d", modifiers: [.command, .option])
            .disabled(store.job.stage.isRunning || !(store.selectedLibraryItem?.canRestoreAudio ?? false))

            Divider()

            Button("Mark Queue: unread") {
                if let item = store.selectedLibraryItem {
                    store.job.markQueueStatus(.unread, for: item)
                }
            }
            .keyboardShortcut("u", modifiers: [])
            .disabled(store.selectedLibraryItem?.isProcessed ?? true)

            Button("Mark Queue: to process") {
                if let item = store.selectedLibraryItem {
                    store.job.markQueueStatus(.toProcess, for: item)
                }
            }
            .keyboardShortcut("p", modifiers: [])
            .disabled(store.selectedLibraryItem?.isProcessed ?? true)

            Button("Mark Queue: process later") {
                if let item = store.selectedLibraryItem {
                    store.job.markQueueStatus(.processLater, for: item)
                }
            }
            .keyboardShortcut("l", modifiers: [])
            .disabled(store.selectedLibraryItem?.isProcessed ?? true)

            Button("Mark Queue: delete") {
                if let item = store.selectedLibraryItem {
                    store.job.markQueueStatus(.delete, for: item)
                }
            }
            .keyboardShortcut("x", modifiers: [])
            .disabled(store.selectedLibraryItem?.isProcessed ?? true)

            Divider()

            Button(store.selectedLibraryItem.map { $0.isRead ? "Mark Selected as Unread" : "Mark Selected as Read" } ?? "Mark Selected as Read") {
                if let item = store.selectedLibraryItem {
                    withAnimation(ProcessSidebarView.libraryListAnimation) {
                        store.job.markRead(!item.isRead, for: item)
                    }
                }
            }
            .disabled(store.selectedLibraryItem == nil)

            Button(store.selectedLibraryItem.map { store.job.isStarred($0) ? "Unstar Selected" : "Star Selected" } ?? "Star Selected") {
                if let item = store.selectedLibraryItem {
                    store.job.toggleStar(for: item)
                }
            }
            .keyboardShortcut("l", modifiers: [.command, .shift])
            .disabled(store.selectedLibraryItem == nil)

            Menu("Move Selected to Group") {
                ForEach(store.job.availableGroupNames, id: \.self) { groupName in
                    Button(groupName) {
                        if let item = store.selectedLibraryItem {
                            store.job.moveLibraryItem(item, toGroup: groupName)
                        }
                    }
                    .disabled(store.job.stage.isRunning || store.selectedLibraryItem?.groupName == groupName)
                }
            }
            .disabled(store.selectedLibraryItem == nil)
        }

        CommandGroup(after: .help) {
            Button("Reveal Logs") {
                store.revealLogs()
            }
        }
    }
}
