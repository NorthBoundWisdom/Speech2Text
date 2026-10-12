import Foundation

@MainActor
extension JobController {
    @discardableResult
    func refreshLibraryNow() -> Task<Void, Never> {
        Task { [weak self] in
            guard let self else { return }
            await self.refreshLibraryNowAsync()
        }
    }

    func refreshLibraryOnLaunch() {
        refreshLibraryInBackground()
    }

    func refreshLibraryAfterProcessing(runtime _: RuntimeContext) async {
        await refreshLibraryAndWait()
    }

    private func refreshLibraryNowAsync() async {
        await refreshLibraryAndWait()
        libraryRefreshMessage = "Library refreshed"
        message = libraryRefreshMessage
        scheduleLibraryRefreshMessageClear()
    }

    private func scheduleLibraryRefreshMessageClear() {
        let current = libraryRefreshMessage
        Task { [weak self] in
            try? await Task.sleep(nanoseconds: 3_000_000_000)
            await MainActor.run {
                guard self?.libraryRefreshMessage == current else { return }
                self?.libraryRefreshMessage = ""
            }
        }
    }
}
