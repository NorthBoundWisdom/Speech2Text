import SwiftUI
#if canImport(Audio2TextCore)
    import Audio2TextCore
#endif

extension ProcessSidebarView {
    var sourceList: some View {
        ScrollView {
            LazyVStack(alignment: .leading, spacing: SidebarMetrics.sectionSpacing) {
                smartFeedsSection
                librarySection
            }
            .padding(.top, 4)
            .padding(.trailing, 12)
        }
    }

    var processList: some View {
        ScrollView {
            LazyVStack(alignment: .leading, spacing: SidebarMetrics.sectionSpacing) {
                smartFeedsSection
                librarySection
                if isShowingSubscriptions {
                    subscriptionsSection
                } else {
                    itemsSection
                }
            }
            .padding(.top, 4)
            .padding(.trailing, 12)
        }
        .overlay {
            if controller.librarySections.isEmpty && !isShowingSubscriptions {
                Text("No process audio found.")
                    .foregroundStyle(.secondary)
            }
        }
    }

    var smartFeedsSection: some View {
        VStack(alignment: .leading, spacing: SidebarMetrics.rowSpacing) {
            sourceRow(
                title: "Subscriptions",
                iconName: "dot.radiowaves.left.and.right",
                iconColor: .purple,
                count: controller.count(for: .subscriptions),
                isSelected: controller.selectedSidebarSource == .subscriptions
            ) {
                controller.selectSidebarSource(.subscriptions)
            }

            ForEach(SidebarSmartFeed.allCases) { feed in
                sourceRow(
                    title: feed.title,
                    iconName: feed.iconName,
                    iconColor: smartFeedColor(feed),
                    count: controller.count(for: .smart(feed)),
                    isSelected: controller.selectedSidebarSource == .smart(feed)
                ) {
                    controller.selectSidebarSource(.smart(feed))
                }
                .contextMenu {
                    if feed == .unprocessed {
                        let markedItems = controller.markedToProcessItems()
                        Button {
                            controller.processAllMarkedToProcess(workflow: .transcribeAndSummarize)
                        } label: {
                            Label("转写并总结 \(markedItems.count) 个", systemImage: "play.fill")
                        }
                        .disabled(
                            controller.stage.isRunning
                                || markedItems.isEmpty
                                || !controller.isCloudSummaryConfigured
                        )

                        Button {
                            controller.processAllMarkedToProcess(workflow: .localOnly)
                        } label: {
                            Label("仅本地转写 \(markedItems.count) 个", systemImage: "waveform")
                        }
                        .disabled(controller.stage.isRunning || markedItems.isEmpty)

                        Button(role: .destructive) {
                            controller.removeAllMarkedDeleted()
                        } label: {
                            Label("remove all marked deleted", systemImage: "trash")
                        }
                        .disabled(controller.stage.isRunning || controller.markedDeletedItems().isEmpty)
                    }
                }
            }
        }
    }

    var librarySection: some View {
        VStack(alignment: .leading, spacing: SidebarMetrics.rowSpacing) {
            HStack(spacing: 8) {
                sidebarHeader("Folders")
                Spacer()
                LibrarySyncStatusBadge(status: controller.displayedLibrarySyncStatus) {
                    controller.refreshLibrarySyncStatus()
                }
                Button {
                    store.isNewGroupPanelPresented = true
                } label: {
                    Image(systemName: "folder.badge.plus")
                        .font(.system(size: 12, weight: .medium))
                        .frame(width: 22, height: 20)
                }
                .buttonStyle(.plain)
                .foregroundStyle(.secondary)
                .help("新增分组")
                .popover(isPresented: $store.isNewGroupPanelPresented, arrowEdge: .top) {
                    newGroupPanel
                        .padding(14)
                }

                Button {
                    store.showImportPanel()
                } label: {
                    Image(systemName: "plus")
                        .font(.system(size: 12, weight: .medium))
                        .frame(width: 22, height: 20)
                }
                .buttonStyle(.plain)
                .foregroundStyle(.secondary)
                .help("新增记录")
                .padding(.trailing, 6)
            }
            librarySourceRow
            ForEach(controller.librarySections) { section in
                groupSourceRow(section)
            }
        }
    }

    var newGroupPanel: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("New Group")
                .font(.headline)
            TextField("Group name", text: $newGroupName)
                .textFieldStyle(.roundedBorder)
                .onSubmit {
                    createNewGroup()
                }
            HStack(spacing: 8) {
                Button("取消") {
                    store.isNewGroupPanelPresented = false
                    newGroupName = ""
                }
                Spacer()
                Button("创建") {
                    createNewGroup()
                }
                .buttonStyle(.borderedProminent)
                .disabled(newGroupName.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)
            }
        }
        .frame(width: 240)
    }

    func createNewGroup() {
        let trimmedName = newGroupName.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmedName.isEmpty else { return }
        controller.createGroup(named: trimmedName)
        store.isNewGroupPanelPresented = false
        newGroupName = ""
    }

    var librarySourceRow: some View {
        let readCounts = controller.readCounts(for: .library)
        return Button {
            controller.selectSidebarSource(.library)
        } label: {
            sidebarRowContent(
                iconName: "books.vertical",
                iconColor: .secondary,
                title: "Library",
                count: controller.count(for: .library),
                countText: readCounts.displayText,
                accessibilityCountText: readCounts.accessibilityText,
                isSelected: controller.selectedSidebarSource == .library,
                titleContent: {
                    Text("Library")
                        .lineLimit(1)
                        .truncationMode(.tail)
                }
            )
        }
        .buttonStyle(.plain)
    }

    func groupSourceRow(_ section: ProcessLibrarySection) -> some View {
        let source = SidebarSource.group(section.title)
        let readCounts = controller.readCounts(for: source)
        return Button {
            controller.selectSidebarSource(source)
        } label: {
            sidebarRowContent(
                iconName: "folder",
                iconColor: .secondary,
                title: section.title,
                count: controller.count(for: source),
                countText: readCounts.displayText,
                accessibilityCountText: readCounts.accessibilityText,
                isSelected: controller.selectedSidebarSource == source,
                titleContent: {
                    if renamingGroupID == section.id {
                        TextField("Group name", text: $renamingGroupName)
                            .textFieldStyle(.plain)
                            .font(.system(size: SidebarMetrics.titleFontSize, weight: .regular))
                            .onSubmit {
                                commitGroupRename(section)
                            }
                    } else {
                        Text(section.title)
                            .lineLimit(1)
                            .truncationMode(.tail)
                            .onTapGesture(count: 2) {
                                beginGroupRename(section)
                            }
                    }
                }
            )
        }
        .buttonStyle(.plain)
        .contextMenu {
            Button {
                beginGroupRename(section)
            } label: {
                Label("重命名分组", systemImage: "pencil")
            }
            .disabled(section.title == ProcessLibrary.defaultGroupName)

            Button(role: .destructive) {
                pendingDeleteGroupName = section.title
            } label: {
                Label("删除分组", systemImage: "trash")
            }
            .disabled(controller.stage.isRunning || section.title == ProcessLibrary.defaultGroupName)
        }
    }

    func sourceRow(
        title: String,
        iconName: String,
        iconColor: Color,
        count: Int,
        isSelected: Bool,
        action: @escaping () -> Void
    ) -> some View {
        Button(action: action) {
            sidebarRowContent(
                iconName: iconName,
                iconColor: iconColor,
                title: title,
                count: count,
                isSelected: isSelected,
                titleContent: {
                    Text(title)
                        .lineLimit(1)
                        .truncationMode(.tail)
                }
            )
        }
        .buttonStyle(.plain)
    }

    func sidebarHeader(_ title: String) -> some View {
        Text(title)
            .font(.system(size: SidebarMetrics.headerFontSize, weight: .semibold))
            .foregroundStyle(.secondary)
            .padding(.top, 1)
            .padding(.bottom, 1)
    }

    func sidebarRowContent<TitleContent: View>(
        iconName: String,
        iconColor: Color,
        title: String,
        count: Int,
        countText: String? = nil,
        accessibilityCountText: String? = nil,
        isSelected: Bool,
        @ViewBuilder titleContent: () -> TitleContent
    ) -> some View {
        let displayCountText = countText ?? (count > 0 ? "\(count)" : nil)
        return HStack(spacing: 8) {
            Image(systemName: iconName)
                .font(.system(size: SidebarMetrics.sourceIconSize, weight: .regular))
                .foregroundStyle(isSelected ? Color.white : iconColor)
                .frame(width: SidebarMetrics.sourceIconFrame, height: SidebarMetrics.sourceIconFrame)

            titleContent()
                .font(.system(size: SidebarMetrics.titleFontSize, weight: isSelected ? .semibold : .regular))
                .foregroundStyle(isSelected ? Color.white : Color.primary)

            Spacer(minLength: 8)

            if let displayCountText {
                Text(displayCountText)
                    .font(.system(size: SidebarMetrics.countFontSize, weight: .medium, design: .rounded).monospacedDigit())
                    .foregroundStyle(isSelected ? Color.white : Color.secondary)
                    .lineLimit(1)
            }
        }
        .frame(height: SidebarMetrics.sourceRowHeight)
        .padding(.horizontal, SidebarMetrics.rowHorizontalPadding)
        .background(
            RoundedRectangle(cornerRadius: SidebarMetrics.rowCornerRadius)
                .fill(isSelected ? Color.accentColor : Color.clear)
        )
        .contentShape(Rectangle())
        .accessibilityLabel(accessibilityLabel(title: title, countText: accessibilityCountText ?? displayCountText))
    }

    private func accessibilityLabel(title: String, countText: String?) -> String {
        guard let countText else { return title }
        return "\(title), \(countText)"
    }

    func smartFeedColor(_ feed: SidebarSmartFeed) -> Color {
        switch feed {
        case .today:
            return .orange
        case .unprocessed:
            return .blue
        case .starred:
            return .yellow
        case .archive:
            return .gray
        }
    }

    func beginGroupRename(_ section: ProcessLibrarySection) {
        renamingGroupID = section.id
        renamingGroupName = section.title
    }

    func commitGroupRename(_ section: ProcessLibrarySection) {
        controller.renameGroup(section.title, to: renamingGroupName)
        renamingGroupID = nil
        renamingGroupName = ""
    }
}
