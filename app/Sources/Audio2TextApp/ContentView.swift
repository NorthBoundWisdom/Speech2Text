import SwiftUI

struct ContentView: View {
    @ObservedObject var store: AppStore

    @AppStorage(LibrarySplitViewController.sourceCollapsedKey) private var sourceCollapsed = false
    @AppStorage(LibrarySplitViewController.listCollapsedKey) private var listCollapsed = false

    var body: some View {
        MacLibraryWorkspace(sourceCollapsed: $sourceCollapsed, listCollapsed: $listCollapsed,
                            statusContent: AnyView(ProcessSidebarView(store: store, layoutMode: .statusOnly).frame(width: 360, height: 440))) {
            sourceColumn
        } listColumn: {
            listColumn
        } detailColumn: {
            detailColumn
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .overlay(alignment: .topLeading) {
            Color.clear
                .frame(width: 1, height: 1)
                .popover(isPresented: $store.isInputPanelPresented, arrowEdge: .top) {
                    ImportPanelView(controller: store.job, isPresented: $store.isInputPanelPresented)
                        .padding(16)
                }
        }
        .sheet(isPresented: $store.isSettingsPresented) {
            SettingsView(store: store)
                .frame(width: 860, height: 660)
        }
        .sheet(isPresented: $store.isSRTExportPanelPresented) {
            SRTExportPanelView(controller: store.srtExport, isPresented: $store.isSRTExportPanelPresented)
        }
        .task {
            await store.job.pollLibrarySyncStatus()
        }
    }

    private var sourceColumn: some View {
        VStack(spacing: 0) {
            ProcessSidebarView(store: store, layoutMode: .sourcesOnly)
                .frame(maxWidth: .infinity, maxHeight: .infinity)
        }
    }

    private var listColumn: some View {
        VStack(spacing: 0) {
            ProcessSidebarView(store: store, layoutMode: .itemsOnly)
                .frame(maxWidth: .infinity, maxHeight: .infinity)
        }
    }

    private var detailColumn: some View {
        VStack(spacing: 0) {
            detailTopBar
            DetailPaneView(controller: store.job, readingStyle: store.settings.readingStyle)
                .frame(maxWidth: .infinity, maxHeight: .infinity)
        }
    }

    private var detailTopBar: some View {
        LibraryWorkspaceDetailHeader {
            titleControl
        }
    }

    @ViewBuilder
    private var titleControl: some View {
        if case .subscriptions = store.job.selectedSidebarSource {
            EmptyView()
        } else if let item = store.job.selectedLibraryItem {
            if item.isProcessed {
                Picker("", selection: selectedTabBinding) {
                    ForEach(ContentTab.displayOrder) { tab in
                        Text(tab.title).tag(tab)
                    }
                }
                .pickerStyle(.segmented)
                .labelsHidden()
            } else {
                Picker("", selection: queueStatusBinding) {
                    ForEach(AppQueueStatus.allCases) { status in
                        Text(status.compactTitle).tag(status)
                    }
                }
                .pickerStyle(.segmented)
                .labelsHidden()
            }
        }
    }

    private var selectedTabBinding: Binding<ContentTab> {
        Binding(
            get: { store.job.selectedTab },
            set: { store.job.selectContentTabAfterViewUpdate($0) }
        )
    }

    private var queueStatusBinding: Binding<AppQueueStatus> {
        Binding(
            get: { store.job.selectedLibraryItem?.queueStatus ?? .unread },
            set: { status in
                guard let item = store.job.selectedLibraryItem, !item.isProcessed else { return }
                store.job.markQueueStatusAfterViewUpdate(status, for: item)
            }
        )
    }
}
