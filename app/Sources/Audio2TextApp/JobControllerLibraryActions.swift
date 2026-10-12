import Foundation

extension JobController {
    func selectContentTabAfterViewUpdate(_ tab: ContentTab) {
        Task { @MainActor [weak self] in
            await Task.yield()
            guard let self, selectedTab != tab, visibleContentTabs.contains(tab) else {
                return
            }
            selectedTab = tab
        }
    }

    func markQueueStatusAfterViewUpdate(_ status: AppQueueStatus, for item: ProcessLibraryItem) {
        let itemID = item.id
        Task { @MainActor [weak self] in
            await Task.yield()
            guard let self else { return }
            guard
                let current = libraryItems.first(where: { $0.id == itemID }),
                !current.isProcessed,
                current.queueStatus != status
            else {
                return
            }
            markQueueStatus(status, for: current)
        }
    }

    func isStarred(_ item: ProcessLibraryItem) -> Bool {
        item.isStarred
    }

    func toggleStar(for item: ProcessLibraryItem) {
        do {
            try ProcessLibrary.updateStar(!item.isStarred, for: item)
            logEvent(category: "library", event: "library_item_star_changed", message: "Star state changed", fields: ["item_id": item.id, "is_starred": "\(!item.isStarred)"])
            refreshLibraryAfterLocalMutation()
        } catch {
            message = error.localizedDescription
            logError(category: "library", event: "library_item_star_failed", error: error, fields: ["item_id": item.id])
        }
    }

    func setStar(_ isStarred: Bool, for items: [ProcessLibraryItem]) {
        let items = uniqueItems(from: items)
        guard !items.isEmpty else {
            message = "No items selected"
            return
        }
        do {
            for item in items {
                try ProcessLibrary.updateStar(isStarred, for: item)
            }
            logEvent(
                category: "library",
                event: "library_items_star_changed",
                message: "Star state changed for selected items",
                fields: ["count": "\(items.count)", "is_starred": "\(isStarred)"]
            )
            refreshLibraryAfterLocalMutation()
            message = isStarred
                ? "Starred \(items.count) item\(items.count == 1 ? "" : "s")"
                : "Unstarred \(items.count) item\(items.count == 1 ? "" : "s")"
        } catch {
            message = error.localizedDescription
            logError(category: "library", event: "library_items_star_failed", error: error)
        }
    }

    func markRead(_ isRead: Bool, for item: ProcessLibraryItem) {
        do {
            try ProcessLibrary.updateRead(isRead, for: item)
            logEvent(category: "library", event: "library_item_read_changed", message: "Read state changed", fields: ["item_id": item.id, "is_read": "\(isRead)"])
            refreshLibraryAfterLocalMutation()
        } catch {
            message = error.localizedDescription
            logError(category: "library", event: "library_item_read_failed", error: error, fields: ["item_id": item.id])
        }
    }

    func markRead(_ isRead: Bool, for items: [ProcessLibraryItem]) {
        let items = uniqueItems(from: items)
        guard !items.isEmpty else {
            message = "No items selected"
            return
        }
        do {
            for item in items {
                try ProcessLibrary.updateRead(isRead, for: item)
            }
            logEvent(
                category: "library",
                event: "library_items_read_changed",
                message: "Read state changed for selected items",
                fields: ["count": "\(items.count)", "is_read": "\(isRead)"]
            )
            refreshLibraryAfterLocalMutation()
            message = isRead
                ? "Marked \(items.count) item\(items.count == 1 ? "" : "s") as read"
                : "Marked \(items.count) item\(items.count == 1 ? "" : "s") as unread"
        } catch {
            message = error.localizedDescription
            logError(category: "library", event: "library_items_read_failed", error: error)
        }
    }

    func markQueueStatus(_ status: AppQueueStatus, for item: ProcessLibraryItem) {
        guard item.queueStatus != status else { return }
        do {
            try ProcessLibrary.updateQueueStatus(status, for: item)
            logEvent(
                category: "library",
                event: "library_item_queue_status_changed",
                message: "Queue status changed",
                fields: ["item_id": item.id, "queue_status": status.rawValue]
            )
            refreshLibraryAfterLocalMutation()
            if selectedLibraryItemID == item.id, let updated = selectedLibraryItem {
                metadataText = ProcessLibrary.metadataText(for: updated)
            }
        } catch {
            message = error.localizedDescription
            logError(category: "library", event: "library_item_queue_status_failed", error: error, fields: ["item_id": item.id])
        }
    }

    func markQueueStatus(_ status: AppQueueStatus, for items: [ProcessLibraryItem]) {
        let candidates = unprocessedItems(from: items)
        guard !candidates.isEmpty else {
            message = "No unprocessed items selected"
            return
        }
        let items = candidates.filter { $0.queueStatus != status }
        guard !items.isEmpty else {
            message = "No queue status changes needed"
            return
        }
        do {
            for item in items {
                try ProcessLibrary.updateQueueStatus(status, for: item)
            }
            logEvent(
                category: "library",
                event: "library_items_queue_status_changed",
                message: "Queue status changed for selected items",
                fields: ["count": "\(items.count)", "queue_status": status.rawValue]
            )
            refreshLibraryAfterLocalMutation()
            if let selectedLibraryItemID, items.contains(where: { $0.id == selectedLibraryItemID }), let updated = selectedLibraryItem {
                metadataText = ProcessLibrary.metadataText(for: updated)
            }
            message = "Marked \(items.count) item\(items.count == 1 ? "" : "s") as \(status.compactTitle)"
        } catch {
            message = error.localizedDescription
            logError(category: "library", event: "library_items_queue_status_failed", error: error)
        }
    }

    func markedToProcessItems() -> [ProcessLibraryItem] {
        libraryItems.filter { item in
            itemIsUnprocessed(item)
                && !item.isArchived
                && item.queueStatus == .toProcess
                && (item.isAudioPresent || item.canRestoreAudio)
        }
    }

    func markedDeletedItems() -> [ProcessLibraryItem] {
        libraryItems.filter { item in
            itemIsUnprocessed(item) && !item.isArchived && item.queueStatus == .delete
        }
    }

    func removeAllMarkedDeleted() {
        guard !stage.isRunning else { return }
        let items = markedDeletedItems()
        guard !items.isEmpty else {
            message = "No deleted marks to remove"
            return
        }
        do {
            for item in items {
                try ProcessLibraryOperations.deleteItem(item)
            }
            if let selectedLibraryItemID, items.contains(where: { $0.id == selectedLibraryItemID }) {
                clearLibrarySelection()
            }
            refreshLibraryAfterLocalMutation()
            message = "Removed \(items.count) marked item\(items.count == 1 ? "" : "s")"
            logEvent(category: "library", event: "remove_all_marked_deleted", message: message, fields: ["count": "\(items.count)"])
        } catch {
            message = error.localizedDescription
            logError(category: "library", event: "remove_marked_deleted_failed", error: error)
        }
    }

    func archiveLibraryItems(_ selectedItems: [ProcessLibraryItem]) {
        guard !stage.isRunning else { return }
        let items = uniqueItems(from: selectedItems).filter { !$0.isArchived }
        guard !items.isEmpty else {
            message = "No items selected"
            return
        }
        do {
            for item in items {
                try ProcessLibraryOperations.archiveItem(item)
            }
            if let selectedLibraryItemID, items.contains(where: { $0.id == selectedLibraryItemID }) {
                clearLibrarySelection()
            }
            refreshLibraryAfterLocalMutation()
            message = "Archived \(items.count) item\(items.count == 1 ? "" : "s")"
            logEvent(category: "library", event: "library_items_archived", message: message, fields: ["count": "\(items.count)"])
        } catch {
            message = error.localizedDescription
            logError(category: "library", event: "library_items_archive_failed", error: error)
        }
    }

    func unarchiveLibraryItems(_ selectedItems: [ProcessLibraryItem]) {
        guard !stage.isRunning else { return }
        let items = uniqueItems(from: selectedItems).filter(\.isArchived)
        guard !items.isEmpty else {
            message = "No archived items selected"
            return
        }
        do {
            for item in items {
                try ProcessLibraryOperations.unarchiveItem(item)
            }
            refreshLibraryAfterLocalMutation()
            if let selectedLibraryItemID, items.contains(where: { $0.id == selectedLibraryItemID }), let updated = selectedLibraryItem {
                metadataText = ProcessLibrary.metadataText(for: updated)
            }
            message = "Unarchived \(items.count) item\(items.count == 1 ? "" : "s")"
            logEvent(category: "library", event: "library_items_unarchived", message: message, fields: ["count": "\(items.count)"])
        } catch {
            message = error.localizedDescription
            logError(category: "library", event: "library_items_unarchive_failed", error: error)
        }
    }

    func deleteLibraryItems(_ selectedItems: [ProcessLibraryItem]) {
        guard !stage.isRunning else { return }
        let items = uniqueItems(from: selectedItems)
        guard !items.isEmpty else {
            message = "No items selected"
            return
        }
        do {
            for item in items {
                try ProcessLibraryOperations.deleteItem(item)
            }
            if let selectedLibraryItemID, items.contains(where: { $0.id == selectedLibraryItemID }) {
                clearLibrarySelection()
            }
            refreshLibraryAfterLocalMutation()
            message = "Deleted \(items.count) item\(items.count == 1 ? "" : "s")"
            logEvent(category: "library", event: "library_items_deleted", message: message, fields: ["count": "\(items.count)"])
        } catch {
            message = error.localizedDescription
            logError(category: "library", event: "library_items_delete_failed", error: error)
        }
    }

    func moveLibraryItems(_ selectedItems: [ProcessLibraryItem], toGroup groupName: String) {
        guard !stage.isRunning else { return }
        let items = uniqueItems(from: selectedItems)
        guard !items.isEmpty else {
            message = "No items selected"
            return
        }
        do {
            var movedCount = 0
            for item in items {
                let result = try ProcessLibraryOperations.moveItem(
                    item,
                    toGroup: groupName,
                    dataRoot: settingsStore.dataRoot()
                )
                if result.moved {
                    movedCount += 1
                }
            }
            message = movedCount == 0 ? "Already in \(groupName)" : "Moved \(movedCount) item\(movedCount == 1 ? "" : "s") to \(groupName)"
            logEvent(category: "library", event: "library_items_moved", message: message, fields: ["count": "\(items.count)", "moved_count": "\(movedCount)", "group": groupName])
            refreshLibraryAfterLocalMutation()
            if let selectedLibraryItemID, items.contains(where: { $0.id == selectedLibraryItemID }), let updated = selectedLibraryItem {
                metadataText = ProcessLibrary.metadataText(for: updated)
            }
        } catch {
            message = error.localizedDescription
            logError(category: "library", event: "library_items_move_failed", error: error, fields: ["group": groupName])
        }
    }

    func cleanupCache(for selectedItems: [ProcessLibraryItem]) {
        guard !stage.isRunning else { return }
        let items = uniqueItems(from: selectedItems)
        guard !items.isEmpty else {
            message = "No items selected"
            return
        }
        do {
            var deletedCount = 0
            var freedBytes: Int64 = 0
            for item in items {
                let result = try ProcessLibraryOperations.cleanupCache(for: item)
                deletedCount += result.deletedCount
                freedBytes += result.freedBytes
            }
            refreshLibraryAfterLocalMutation()
            if let selectedLibraryItemID, items.contains(where: { $0.id == selectedLibraryItemID }), let updated = selectedLibraryItem {
                metadataText = ProcessLibrary.metadataText(for: updated)
                snapshot = snapshotForOutputDirectory(updated.outputURL)
            }
            let freedMB = Double(freedBytes) / 1_048_576.0
            message = "Cleaned \(deletedCount) cache item\(deletedCount == 1 ? "" : "s"), freed \(String(format: "%.1f", freedMB)) MB"
            logEvent(category: "library", event: "library_items_cache_cleaned", message: message, fields: ["count": "\(items.count)", "deleted_count": "\(deletedCount)", "freed_bytes": "\(freedBytes)"])
        } catch {
            message = error.localizedDescription
            logError(category: "library", event: "library_items_cache_cleanup_failed", error: error)
        }
    }

    func moveLibraryItem(_ item: ProcessLibraryItem, toGroup groupName: String) {
        guard !stage.isRunning else { return }
        do {
            let result = try ProcessLibraryOperations.moveItem(
                item,
                toGroup: groupName,
                dataRoot: settingsStore.dataRoot()
            )
            if selectedLibraryItemID == item.id {
                metadataText = ProcessLibrary.metadataText(for: item)
            }
            message = result.moved ? "Moved to \(groupName)" : "Already in \(groupName)"
            logEvent(category: "library", event: "library_item_moved", message: message, fields: ["item_id": item.id, "group": groupName])
            refreshLibraryAfterLocalMutation()
        } catch {
            message = error.localizedDescription
            logError(category: "library", event: "library_item_move_failed", error: error, fields: ["item_id": item.id, "group": groupName])
        }
    }

    func createGroup(named name: String) {
        let groupPath = ProcessLibrary.pathComponent(forGroupName: name)
        do {
            try ProcessLibrary.createGroup(groupPath, in: settingsStore.libraryRoot())
            refreshLibraryAfterLocalMutation()
            message = "Created group \(groupPath)"
            logEvent(category: "library", event: "group_created", message: "Group created", fields: ["group": groupPath])
        } catch {
            message = error.localizedDescription
            logError(category: "library", event: "group_create_failed", error: error, fields: ["group": groupPath])
        }
    }

    func deleteGroup(_ groupName: String) {
        guard !stage.isRunning else { return }
        do {
            let result = try ProcessLibraryOperations.deleteGroup(groupName, dataRoot: settingsStore.dataRoot())
            guard result.deleted else { return }
            if selectedGroupName == result.groupName {
                selectedGroupName = ProcessLibrary.defaultGroupName
            }
            if sidebarGroupName == result.groupName {
                selectedSidebarSource = .group(ProcessLibrary.defaultGroupName)
            }
            refreshLibraryAfterLocalMutation()
            message = result.movedItemCount > 0
                ? "Deleted group \(result.groupName); moved \(result.movedItemCount) item\(result.movedItemCount == 1 ? "" : "s") to \(ProcessLibrary.defaultGroupName)"
                : "Deleted group \(result.groupName)"
            logEvent(
                category: "library",
                event: "group_deleted",
                message: message,
                fields: ["group": result.groupName, "moved_count": "\(result.movedItemCount)"]
            )
        } catch {
            message = error.localizedDescription
            logError(category: "library", event: "group_delete_failed", error: error, fields: ["group": groupName])
        }
    }

    func renameGroup(_ oldName: String, to newName: String) {
        do {
            let result = try ProcessLibraryOperations.renameGroup(
                oldName,
                to: newName,
                dataRoot: settingsStore.dataRoot()
            )
            guard result.groupName != ProcessLibrary.pathComponent(forGroupName: oldName) else { return }
            if selectedGroupName == oldName || result.oldComponents.contains(selectedGroupName) {
                selectedGroupName = result.groupName
            }
            if result.oldComponents.contains(sidebarGroupName) {
                selectedSidebarSource = .group(result.groupName)
            }
            refreshLibraryAfterLocalMutation()
            message = "Renamed group to \(result.groupName)"
            logEvent(category: "library", event: "group_renamed", message: message, fields: ["old_group": oldName, "new_group": result.groupName])
        } catch {
            message = error.localizedDescription
            logError(category: "library", event: "group_rename_failed", error: error, fields: ["old_group": oldName])
        }
    }

    func deleteLibraryItem(_ item: ProcessLibraryItem) {
        guard !stage.isRunning else { return }
        do {
            try ProcessLibraryOperations.deleteItem(item)
            if selectedLibraryItemID == item.id {
                clearLibrarySelection()
                message = "Deleted"
            }
            refreshLibraryAfterLocalMutation()
            logEvent(category: "library", event: "library_item_deleted", message: "Library item deleted", fields: ["item_id": item.id])
        } catch {
            message = error.localizedDescription
            logError(category: "library", event: "library_item_delete_failed", error: error, fields: ["item_id": item.id])
        }
    }

    func archiveLibraryItem(_ item: ProcessLibraryItem) {
        archiveLibraryItems([item])
    }

    func unarchiveLibraryItem(_ item: ProcessLibraryItem) {
        unarchiveLibraryItems([item])
    }
}
