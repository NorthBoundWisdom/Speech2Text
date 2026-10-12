import AppKit
import SwiftUI
#if canImport(Audio2TextCore)
    import Audio2TextCore
#endif

extension ProcessSidebarView {
    @ViewBuilder
    func processItemContextMenu(for item: ProcessLibraryItem) -> some View {
        let actionItems = contextItems(for: item)
        let unprocessedActionItems = actionItems.filter { !$0.isProcessed }
        let processedActionItems = actionItems.filter(\.isProcessed)
        let multipleSelection = actionItems.count > 1
        let isUnprocessedContext = actionItems.allSatisfy { !$0.isProcessed }
        let isArchiveContext = actionItems.allSatisfy(\.isArchived)

        Button {
            copyTitlesToPasteboard(actionItems)
        } label: {
            Label(multipleSelection ? "复制 \(actionItems.count) 项标题" : "复制标题", systemImage: "doc.on.doc")
        }

        Divider()

        if isArchiveContext {
            Button {
                controller.unarchiveLibraryItems(actionItems)
                selectedItemIDs = Set(actionItems.map(\.id))
            } label: {
                Label(multipleSelection ? "取消归档 \(actionItems.count) 项" : "取消归档", systemImage: "tray.and.arrow.up")
            }
            .disabled(controller.stage.isRunning)

            Divider()

            Button(role: .destructive) {
                if multipleSelection {
                    pendingBulkDeleteItems = actionItems
                } else if let archivedItem = actionItems.first {
                    pendingDeleteItem = archivedItem
                }
            } label: {
                Label(multipleSelection ? "删除 \(actionItems.count) 项" : "删除", systemImage: "trash")
            }
            .disabled(controller.stage.isRunning)
        }

        if !isArchiveContext && isUnprocessedContext {
            unprocessedItemContextMenu(for: actionItems)
        }

        if !isArchiveContext && !isUnprocessedContext && actionItems.count > 1 {
            if isShowingUnprocessedItems, !unprocessedActionItems.isEmpty {
                Menu {
                    ForEach(AppQueueStatus.allCases) { status in
                        Button {
                            controller.markQueueStatus(status, for: unprocessedActionItems)
                            selectedItemIDs = Set(unprocessedActionItems.map(\.id))
                        } label: {
                            Label(status.compactTitle, systemImage: queueStatusIcon(for: status))
                        }
                    }
                } label: {
                    Label("标记未处理项为", systemImage: "flag")
                }

                Button {
                    controller.processLibraryItems(unprocessedActionItems, workflow: .transcribeAndSummarize)
                    clearItemSelection()
                } label: {
                    Label("转写并总结未处理项 \(unprocessedActionItems.count) 个", systemImage: "play.fill")
                }
                .disabled(
                    controller.stage.isRunning
                        || unprocessedActionItems.allSatisfy {
                            !controller.canProcessLibraryItem($0, reprocess: $0.needsReanalysis, workflow: .transcribeAndSummarize)
                        }
                )

                Button {
                    controller.processLibraryItems(unprocessedActionItems, workflow: .localOnly)
                    clearItemSelection()
                } label: {
                    Label("仅本地转写未处理项 \(unprocessedActionItems.count) 个", systemImage: "waveform")
                }
                .disabled(
                    controller.stage.isRunning
                        || unprocessedActionItems.allSatisfy {
                            !controller.canProcessLibraryItem($0, reprocess: $0.needsReanalysis, workflow: .localOnly)
                        }
                )
            }

            if !processedActionItems.isEmpty {
                Button {
                    controller.reprocessLibraryItems(processedActionItems, workflow: .transcribeAndSummarize)
                    clearItemSelection()
                } label: {
                    Label("重新转写并总结已处理项 \(processedActionItems.count) 个", systemImage: "arrow.clockwise")
                }
                .disabled(
                    controller.stage.isRunning
                        || processedActionItems.allSatisfy {
                            !controller.canProcessLibraryItem($0, reprocess: true, workflow: .transcribeAndSummarize)
                        }
                )

                Button {
                    controller.reprocessLibraryItems(processedActionItems, workflow: .localOnly)
                    clearItemSelection()
                } label: {
                    Label("仅重新本地转写已处理项 \(processedActionItems.count) 个", systemImage: "waveform")
                }
                .disabled(
                    controller.stage.isRunning
                        || processedActionItems.allSatisfy {
                            !controller.canProcessLibraryItem($0, reprocess: true, workflow: .localOnly)
                        }
                )

                Button {
                    if multipleSelection {
                        controller.regenerateSummaries(for: processedActionItems)
                        clearItemSelection()
                    } else if let summaryItem = processedActionItems.first {
                        controller.regenerateSummaryDiscardingExisting(for: summaryItem)
                    }
                } label: {
                    Label(
                        multipleSelection ? "重新生成总结 \(processedActionItems.count) 个" : "重新生成总结",
                        systemImage: "text.badge.star"
                    )
                }
                .disabled(controller.stage.isRunning || processedActionItems.allSatisfy { !controller.canGenerateSummary(for: $0) })

                Button {
                    controller.regenerateTitles(for: processedActionItems)
                    clearItemSelection()
                } label: {
                    Label("重新生成标题 \(processedActionItems.count) 个", systemImage: "textformat")
                }
                .disabled(controller.stage.isRunning || processedActionItems.allSatisfy { !controller.canRegenerateTitle(for: $0) })
            }

            Button {
                let shouldRead = actionItems.contains { !$0.isRead }
                withAnimation(Self.libraryListAnimation) {
                    controller.markRead(shouldRead, for: actionItems)
                    clearItemSelection()
                }
            } label: {
                Label(
                    actionItems.contains(where: { !$0.isRead }) ? "标记 \(actionItems.count) 项为已读" : "标记 \(actionItems.count) 项为未读",
                    systemImage: actionItems.contains(where: { !$0.isRead }) ? "checkmark.circle" : "circle"
                )
            }
            .disabled(controller.stage.isRunning)

            Button {
                let shouldStar = actionItems.contains { !$0.isStarred }
                controller.setStar(shouldStar, for: actionItems)
                clearItemSelection()
            } label: {
                Label(
                    actionItems.contains(where: { !$0.isStarred }) ? "星标 \(actionItems.count) 项" : "取消 \(actionItems.count) 项星标",
                    systemImage: actionItems.contains(where: { !$0.isStarred }) ? "star" : "star.slash"
                )
            }
            .disabled(controller.stage.isRunning)

            Menu {
                ForEach(controller.availableGroupNames, id: \.self) { groupName in
                    Button(groupName) {
                        controller.moveLibraryItems(actionItems, toGroup: groupName)
                        selectedItemIDs = Set(actionItems.map(\.id))
                    }
                    .disabled(controller.stage.isRunning || actionItems.allSatisfy { $0.groupName == groupName })
                }
            } label: {
                Label("移动 \(actionItems.count) 项到分组", systemImage: "folder")
            }

            Button {
                controller.archiveLibraryItems(actionItems)
                clearItemSelection()
            } label: {
                Label("归档 \(actionItems.count) 项", systemImage: "archivebox")
            }
            .disabled(controller.stage.isRunning)

            Button {
                controller.cleanupCache(for: actionItems)
                clearItemSelection()
            } label: {
                Label("清理 \(actionItems.count) 项缓存", systemImage: "externaldrive.badge.minus")
            }
            .disabled(controller.stage.isRunning)

            Button(role: .destructive) {
                pendingBulkDeleteItems = actionItems
            } label: {
                Label("删除 \(actionItems.count) 项", systemImage: "trash")
            }
            .disabled(controller.stage.isRunning)

            Divider()
        }

        if !isArchiveContext && !isUnprocessedContext && !multipleSelection && item.isProcessed && !item.hasFile {
            Button {
                controller.restoreAudio(for: item)
            } label: {
                Label("重新下载音频", systemImage: "arrow.down.circle")
            }
            .disabled(controller.stage.isRunning || !item.canRestoreAudio)
        }

        if !isArchiveContext && !isUnprocessedContext && !multipleSelection {
            processingActionButton(for: item, workflow: .transcribeAndSummarize)
            processingActionButton(for: item, workflow: .localOnly)
        }

        if !isArchiveContext && !isUnprocessedContext && !multipleSelection && item.isProcessed {
            Button {
                controller.regenerateSummaryDiscardingExisting(for: item)
            } label: {
                Label("重新生成总结", systemImage: "text.badge.star")
            }
            .disabled(!controller.canGenerateSummary(for: item))

            Button {
                controller.regenerateTitle(for: item)
            } label: {
                Label("重新生成标题", systemImage: "textformat")
            }
            .disabled(!controller.canRegenerateTitle(for: item))
        }

        if !isArchiveContext && !isUnprocessedContext && !multipleSelection {
            Button {
                NSWorkspace.shared.open(item.audioURL.deletingLastPathComponent())
            } label: {
                Label("打开数据文件夹", systemImage: "folder")
            }

            if FileManager.default.fileExists(atPath: item.outputURL.path) {
                Button {
                    NSWorkspace.shared.open(item.outputURL)
                } label: {
                    Label("打开产物文件夹", systemImage: "shippingbox")
                }
            }
        }

        if !isArchiveContext && !isUnprocessedContext && !multipleSelection {
            Button {
                withAnimation(Self.libraryListAnimation) {
                    controller.markRead(!item.isRead, for: item)
                }
            } label: {
                Label(item.isRead ? "标记为未读" : "标记为已读", systemImage: item.isRead ? "circle" : "checkmark.circle")
            }

            Button {
                controller.toggleStar(for: item)
            } label: {
                Label(item.isStarred ? "取消星标" : "星标", systemImage: item.isStarred ? "star.slash" : "star")
            }

            Menu {
                ForEach(controller.availableGroupNames, id: \.self) { groupName in
                    if groupName == item.groupName {
                        Button {} label: {
                            Label(groupName, systemImage: "checkmark")
                        }
                        .disabled(true)
                    } else {
                        Button(groupName) {
                            controller.moveLibraryItem(item, toGroup: groupName)
                        }
                        .disabled(controller.stage.isRunning)
                    }
                }
            } label: {
                Label("移动到分组", systemImage: "folder")
            }

            Button {
                controller.cleanupCache(for: [item])
            } label: {
                Label("清理缓存", systemImage: "externaldrive.badge.minus")
            }
            .disabled(controller.stage.isRunning)

            Button {
                controller.archiveLibraryItem(item)
            } label: {
                Label("归档", systemImage: "archivebox")
            }
            .disabled(controller.stage.isRunning)

            Divider()

            Button(role: .destructive) {
                pendingDeleteItem = item
            } label: {
                Label("删除", systemImage: "trash")
            }
            .disabled(controller.stage.isRunning)
        }
    }

    @ViewBuilder
    func unprocessedItemContextMenu(for actionItems: [ProcessLibraryItem]) -> some View {
        let multipleSelection = actionItems.count > 1
        let downloadableItems = actionItems.filter(\.canDownloadAudio)

        Button {
            if multipleSelection {
                controller.processLibraryItems(actionItems, workflow: .transcribeAndSummarize)
                clearItemSelection()
            } else if let item = actionItems.first {
                controller.processLibraryItem(item, reprocess: item.needsReanalysis, workflow: .transcribeAndSummarize)
            }
        } label: {
            Label(
                multipleSelection
                    ? "转写并总结 \(actionItems.count) 个"
                    : ProcessingWorkflow.transcribeAndSummarize.actionTitle(isCloudConfigured: controller.isCloudSummaryConfigured),
                systemImage: "play.fill"
            )
        }
        .disabled(
            controller.stage.isRunning
                || actionItems.allSatisfy {
                    !controller.canProcessLibraryItem($0, reprocess: $0.needsReanalysis, workflow: .transcribeAndSummarize)
                }
        )

        Button {
            if multipleSelection {
                controller.processLibraryItems(actionItems, workflow: .localOnly)
                clearItemSelection()
            } else if let item = actionItems.first {
                controller.processLibraryItem(item, reprocess: item.needsReanalysis, workflow: .localOnly)
            }
        } label: {
            Label(
                multipleSelection
                    ? "仅本地转写 \(actionItems.count) 个"
                    : ProcessingWorkflow.localOnly.actionTitle(),
                systemImage: "waveform"
            )
        }
        .disabled(
            controller.stage.isRunning
                || actionItems.allSatisfy {
                    !controller.canProcessLibraryItem($0, reprocess: $0.needsReanalysis, workflow: .localOnly)
                }
        )

        if !downloadableItems.isEmpty {
            Button {
                if multipleSelection {
                    controller.downloadAudio(for: downloadableItems)
                    clearItemSelection()
                } else if let item = downloadableItems.first {
                    controller.downloadAudio(for: item)
                }
            } label: {
                Label(multipleSelection ? "下载音频 \(downloadableItems.count) 个" : "下载音频", systemImage: "arrow.down.circle")
            }
            .disabled(controller.stage.isRunning || downloadableItems.allSatisfy { !controller.canDownloadAudio(for: $0) })
        }

        ForEach(AppQueueStatus.allCases) { status in
            Button {
                controller.markQueueStatus(status, for: actionItems)
                selectedItemIDs = Set(actionItems.map(\.id))
            } label: {
                if actionItems.allSatisfy({ $0.queueStatus == status }) {
                    Label("Flag: \(status.compactTitle)", systemImage: "checkmark")
                } else {
                    Label("Flag: \(status.compactTitle)", systemImage: queueStatusIcon(for: status))
                }
            }
        }
        .disabled(controller.stage.isRunning)

        Divider()

        Button {
            controller.archiveLibraryItems(actionItems)
            clearItemSelection()
        } label: {
            Label(multipleSelection ? "归档 \(actionItems.count) 个" : "归档", systemImage: "archivebox")
        }
        .disabled(controller.stage.isRunning)

        Button(role: .destructive) {
            if multipleSelection {
                pendingBulkDeleteItems = actionItems
            } else if let item = actionItems.first {
                pendingDeleteItem = item
            }
        } label: {
            Label(multipleSelection ? "删除 \(actionItems.count) 个" : "删除", systemImage: "trash")
        }
        .disabled(controller.stage.isRunning)
    }
}
