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
            Label(multipleSelection ? "Copy \(actionItems.count) item titles" : "Copy title", systemImage: "doc.on.doc")
        }

        Divider()

        if isArchiveContext {
            Button {
                controller.unarchiveLibraryItems(actionItems)
                selectedItemIDs = Set(actionItems.map(\.id))
            } label: {
                Label(multipleSelection ? "Unarchive \(actionItems.count) items" : "Unarchive", systemImage: "tray.and.arrow.up")
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
                Label(multipleSelection ? "Delete \(actionItems.count) items" : "Delete", systemImage: "trash")
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
                    Label("Mark unprocessed items as", systemImage: "flag")
                }

                Button {
                    controller.processLibraryItems(unprocessedActionItems, workflow: .transcribeAndSummarize)
                    clearItemSelection()
                } label: {
                    Label("Transcribe and summarize \(unprocessedActionItems.count) unprocessed items", systemImage: "play.fill")
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
                    Label("Transcribe \(unprocessedActionItems.count) unprocessed items locally", systemImage: "waveform")
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
                    Label("Retranscribe and summarize \(processedActionItems.count) processed items", systemImage: "arrow.clockwise")
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
                    Label("Retranscribe \(processedActionItems.count) processed items locally", systemImage: "waveform")
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
                        multipleSelection ? "Regenerate \(processedActionItems.count) summaries" : "Regenerate summary",
                        systemImage: "text.badge.star"
                    )
                }
                .disabled(controller.stage.isRunning || processedActionItems.allSatisfy { !controller.canGenerateSummary(for: $0) })

                Button {
                    controller.regenerateTitles(for: processedActionItems)
                    clearItemSelection()
                } label: {
                    Label("Regenerate \(processedActionItems.count) titles", systemImage: "textformat")
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
                    actionItems.contains(where: { !$0.isRead }) ? "Mark \(actionItems.count) items read" : "Mark \(actionItems.count) items unread",
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
                    actionItems.contains(where: { !$0.isStarred }) ? "Star \(actionItems.count) items" : "Unstar \(actionItems.count) items",
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
                Label("Move \(actionItems.count) items to group", systemImage: "folder")
            }

            Button {
                controller.archiveLibraryItems(actionItems)
                clearItemSelection()
            } label: {
                Label("Archive \(actionItems.count) items", systemImage: "archivebox")
            }
            .disabled(controller.stage.isRunning)

            Button {
                controller.cleanupCache(for: actionItems)
                clearItemSelection()
            } label: {
                Label("Clear cache for \(actionItems.count) items", systemImage: "externaldrive.badge.minus")
            }
            .disabled(controller.stage.isRunning)

            Button(role: .destructive) {
                pendingBulkDeleteItems = actionItems
            } label: {
                Label("Delete \(actionItems.count) items", systemImage: "trash")
            }
            .disabled(controller.stage.isRunning)

            Divider()
        }

        if !isArchiveContext && !isUnprocessedContext && !multipleSelection && item.isProcessed && !item.hasFile {
            Button {
                controller.restoreAudio(for: item)
            } label: {
                Label("Download audio again", systemImage: "arrow.down.circle")
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
                Label("Regenerate summary", systemImage: "text.badge.star")
            }
            .disabled(!controller.canGenerateSummary(for: item))

            Button {
                controller.regenerateTitle(for: item)
            } label: {
                Label("Regenerate title", systemImage: "textformat")
            }
            .disabled(!controller.canRegenerateTitle(for: item))
        }

        if !isArchiveContext && !isUnprocessedContext && !multipleSelection {
            Button {
                NSWorkspace.shared.open(item.audioURL.deletingLastPathComponent())
            } label: {
                Label("Open data folder", systemImage: "folder")
            }

            if FileManager.default.fileExists(atPath: item.outputURL.path) {
                Button {
                    NSWorkspace.shared.open(item.outputURL)
                } label: {
                    Label("Open output folder", systemImage: "shippingbox")
                }
            }
        }

        if !isArchiveContext && !isUnprocessedContext && !multipleSelection {
            Button {
                withAnimation(Self.libraryListAnimation) {
                    controller.markRead(!item.isRead, for: item)
                }
            } label: {
                Label(item.isRead ? "Mark unread" : "Mark read", systemImage: item.isRead ? "circle" : "checkmark.circle")
            }

            Button {
                controller.toggleStar(for: item)
            } label: {
                Label(item.isStarred ? "Unstar" : "Star", systemImage: item.isStarred ? "star.slash" : "star")
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
                Label("Move to group", systemImage: "folder")
            }

            Button {
                controller.cleanupCache(for: [item])
            } label: {
                Label("Clear cache", systemImage: "externaldrive.badge.minus")
            }
            .disabled(controller.stage.isRunning)

            Button {
                controller.archiveLibraryItem(item)
            } label: {
                Label("Archive", systemImage: "archivebox")
            }
            .disabled(controller.stage.isRunning)

            Divider()

            Button(role: .destructive) {
                pendingDeleteItem = item
            } label: {
                Label("Delete", systemImage: "trash")
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
                    ? "Transcribe and summarize \(actionItems.count) items"
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
                    ? "Transcribe \(actionItems.count) items locally"
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
                Label(multipleSelection ? "Download \(downloadableItems.count) audio files" : "Download audio", systemImage: "arrow.down.circle")
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
            Label(multipleSelection ? "Archive \(actionItems.count) items" : "Archive", systemImage: "archivebox")
        }
        .disabled(controller.stage.isRunning)

        Button(role: .destructive) {
            if multipleSelection {
                pendingBulkDeleteItems = actionItems
            } else if let item = actionItems.first {
                pendingDeleteItem = item
            }
        } label: {
            Label(multipleSelection ? "Delete \(actionItems.count) items" : "Delete", systemImage: "trash")
        }
        .disabled(controller.stage.isRunning)
    }
}
