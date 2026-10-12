import Foundation

extension JobController {
    func addSubscription() {
        guard !stage.isRunning, !isAddingSubscription, !isRefreshingSubscriptions else { return }
        let url = subscriptionURLText.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !url.isEmpty else {
            message = "Enter a subscription URL"
            return
        }
        logEvent(category: "subscriptions", event: "subscription_add_requested", message: "Subscription add requested", fields: ["host": URL(string: url)?.host ?? "", "group": subscriptionGroupName])
        currentTask?.cancel()
        currentTask = Task { await runAddSubscription(url: url, groupName: subscriptionGroupName) }
    }

    func refreshAllSubscriptions() {
        guard !stage.isRunning, !isAddingSubscription, !isRefreshingSubscriptions else { return }
        logEvent(category: "subscriptions", event: "subscriptions_refresh_all_requested", message: "Refresh all subscriptions requested")
        currentTask?.cancel()
        currentTask = Task { await runRefreshSubscriptions(id: nil) }
    }

    func refreshSubscription(_ subscription: PodcastSubscriptionItem) {
        guard !stage.isRunning, !isAddingSubscription, !isRefreshingSubscriptions else { return }
        logEvent(category: "subscriptions", event: "subscription_refresh_requested", message: "Subscription refresh requested", fields: ["subscription_id": subscription.id])
        currentTask?.cancel()
        currentTask = Task { await runRefreshSubscriptions(id: subscription.id, fullHistory: false) }
    }

    func fetchSubscriptionHistory(_ subscription: PodcastSubscriptionItem) {
        guard !stage.isRunning, !isAddingSubscription, !isRefreshingSubscriptions else { return }
        logEvent(category: "subscriptions", event: "subscription_history_fetch_requested", message: "Subscription full history fetch requested", fields: ["subscription_id": subscription.id])
        currentTask?.cancel()
        currentTask = Task { await runRefreshSubscriptions(id: subscription.id, fullHistory: true) }
    }

    func removeSubscription(_ subscription: PodcastSubscriptionItem) {
        guard !stage.isRunning, !isAddingSubscription, !isRefreshingSubscriptions else { return }
        logEvent(category: "subscriptions", event: "subscription_remove_requested", message: "Subscription remove requested", fields: ["subscription_id": subscription.id])
        currentTask?.cancel()
        currentTask = Task { await runRemoveSubscription(id: subscription.id) }
    }

    func runAddSubscription(url: String, groupName: String) async {
        isAddingSubscription = true
        message = "Adding subscription"
        do {
            let runtime = try runtimeProvider()
            _ = try await runSubscriptionsCommand(
                ["add", url, "--group-name", groupName, "--limit", "10", "--json"],
                runtime: runtime
            )
            subscriptionURLText = ""
            subscriptionGroupName = ProcessLibrary.pathComponent(forGroupName: groupName)
            await refreshLibraryAndWait()
            message = "Subscription added"
            logEvent(category: "subscriptions", event: "subscription_added", message: "Subscription added", fields: ["host": URL(string: url)?.host ?? "", "group": groupName])
        } catch {
            message = error.localizedDescription
            appendLog("\nERROR: \(error.localizedDescription)\n")
            logError(category: "subscriptions", event: "subscription_add_failed", error: error, fields: ["host": URL(string: url)?.host ?? ""])
        }
        isAddingSubscription = false
    }

    func runRefreshSubscriptions(id: String?, fullHistory: Bool = false) async {
        isRefreshingSubscriptions = true
        let operationTitle = fullHistory ? "Fetch subscription history" : "Refresh subscription"
        let selectedSubscriptions = selectedSubscriptionsForRefresh(id: id)
        let total = max(selectedSubscriptions.count, id == nil ? 0 : 1)
        message = fullHistory ? "Fetching subscription history" : "Refreshing subscriptions"
        beginSubscriptionRefreshStatus(
            title: operationTitle,
            itemTitle: selectedSubscriptions.first?.title ?? "",
            detail: total > 0 ? "Preparing refresh 0/\(total)" : "Preparing subscription refresh",
            fraction: 0.02,
            state: .running
        )
        do {
            let runtime = try runtimeProvider()
            if id == nil, !selectedSubscriptions.isEmpty {
                try await runRefreshAllSubscriptions(
                    selectedSubscriptions,
                    fullHistory: fullHistory,
                    title: operationTitle,
                    runtime: runtime
                )
            } else {
                let itemTitle = selectedSubscriptions.first?.title ?? ""
                updateSubscriptionRefreshStatus(
                    title: operationTitle,
                    itemTitle: itemTitle,
                    detail: total > 0 ? "Refreshing 1/\(total)" : "Refreshing subscription",
                    fraction: 0.25,
                    state: .running
                )
                _ = try await runSubscriptionsCommand(
                    refreshSubscriptionArguments(id: id, fullHistory: fullHistory),
                    runtime: runtime
                )
            }
            updateSubscriptionRefreshStatus(
                title: operationTitle,
                itemTitle: "",
                detail: "Sync subscription list",
                fraction: 0.95,
                state: .running
            )
            await refreshLibraryAndWait()
            message = fullHistory ? "Subscription history fetched" : "Subscriptions refreshed"
            updateSubscriptionRefreshStatus(
                title: operationTitle,
                itemTitle: "",
                detail: total > 0 ? "Refreshed \(total)/\(total); sync complete" : "Sync complete",
                fraction: 1.0,
                state: .success
            )
            scheduleSubscriptionRefreshStatusClear()
            logEvent(
                category: "subscriptions",
                event: fullHistory ? "subscription_history_fetched" : "subscriptions_refreshed",
                message: fullHistory ? "Subscription history fetched" : "Subscriptions refreshed",
                fields: ["subscription_id": id ?? "all"]
            )
        } catch {
            message = error.localizedDescription
            appendLog("\nERROR: \(error.localizedDescription)\n")
            updateSubscriptionRefreshStatus(
                title: operationTitle,
                itemTitle: subscriptionRefreshTaskStatus?.itemTitle ?? "",
                detail: "Refresh failed: \(error.localizedDescription)",
                fraction: max(subscriptionRefreshTaskStatus?.fraction ?? 0.10, 0.10),
                state: .failure
            )
            scheduleSubscriptionRefreshStatusClear()
            logError(
                category: "subscriptions",
                event: fullHistory ? "subscription_history_fetch_failed" : "subscriptions_refresh_failed",
                error: error,
                fields: ["subscription_id": id ?? "all"]
            )
        }
        isRefreshingSubscriptions = false
    }

    private func selectedSubscriptionsForRefresh(id: String?) -> [PodcastSubscriptionItem] {
        guard let id else { return subscriptions }
        return subscriptions.filter { $0.id == id }
    }

    private func runRefreshAllSubscriptions(
        _ selectedSubscriptions: [PodcastSubscriptionItem],
        fullHistory: Bool,
        title: String,
        runtime: RuntimeContext
    ) async throws {
        let total = selectedSubscriptions.count
        for (index, subscription) in selectedSubscriptions.enumerated() {
            let completed = index
            updateSubscriptionRefreshStatus(
                title: title,
                itemTitle: subscription.title,
                detail: "Refreshing \(completed + 1)/\(total)",
                fraction: Double(completed) / Double(total),
                state: .running
            )
            _ = try await runSubscriptionsCommand(
                refreshSubscriptionArguments(id: subscription.id, fullHistory: fullHistory),
                runtime: runtime
            )
            updateSubscriptionRefreshStatus(
                title: title,
                itemTitle: subscription.title,
                detail: "Refreshed \(completed + 1)/\(total)",
                fraction: Double(completed + 1) / Double(total),
                state: .running
            )
        }
    }

    private func refreshSubscriptionArguments(id: String?, fullHistory: Bool) -> [String] {
        var arguments = ["refresh"]
        if fullHistory {
            arguments.append("--full-history")
        } else {
            arguments.append(contentsOf: ["--limit", "10"])
        }
        arguments.append("--json")
        if let id {
            arguments.append(contentsOf: ["--id", id])
        } else {
            arguments.append("--all")
        }
        return arguments
    }

    private func beginSubscriptionRefreshStatus(
        title: String,
        itemTitle: String,
        detail: String,
        fraction: Double,
        state: ProcessingTaskState
    ) {
        subscriptionRefreshStatusGeneration += 1
        subscriptionRefreshStatusClearTask?.cancel()
        updateSubscriptionRefreshStatus(
            title: title,
            itemTitle: itemTitle,
            detail: detail,
            fraction: fraction,
            state: state
        )
    }

    private func updateSubscriptionRefreshStatus(
        title: String,
        itemTitle: String,
        detail: String,
        fraction: Double,
        state: ProcessingTaskState
    ) {
        subscriptionRefreshTaskStatus = ProcessingTaskStatus(
            kind: .sync,
            id: "subscription-refresh",
            title: title,
            itemTitle: compactProgressItemTitle(itemTitle),
            detail: detail,
            fraction: fraction,
            state: state
        )
    }

    private func scheduleSubscriptionRefreshStatusClear() {
        let generation = subscriptionRefreshStatusGeneration
        subscriptionRefreshStatusClearTask?.cancel()
        subscriptionRefreshStatusClearTask = Task { [weak self] in
            try? await Task.sleep(nanoseconds: 3_000_000_000)
            await MainActor.run {
                guard self?.subscriptionRefreshStatusGeneration == generation else { return }
                self?.subscriptionRefreshTaskStatus = nil
            }
        }
    }

    func runRemoveSubscription(id: String) async {
        isRefreshingSubscriptions = true
        message = "Removing subscription"
        do {
            let runtime = try runtimeProvider()
            _ = try await runSubscriptionsCommand(["remove", id, "--json"], runtime: runtime)
            loadSubscriptions(dataRoot: runtime.dataRoot)
            message = "Subscription removed"
            logEvent(category: "subscriptions", event: "subscription_removed", message: "Subscription removed", fields: ["subscription_id": id])
        } catch {
            message = error.localizedDescription
            appendLog("\nERROR: \(error.localizedDescription)\n")
            logError(category: "subscriptions", event: "subscription_remove_failed", error: error, fields: ["subscription_id": id])
        }
        isRefreshingSubscriptions = false
    }

    func runSubscriptionsCommand(_ arguments: [String], runtime: RuntimeContext) async throws -> String {
        let commandRunner = SubscriptionCommandRunner(
            runner: runner,
            outputHandler: appendLog,
            logger: { [weak self] event, fields in
                self?.logEvent(
                    category: "subscriptions",
                    event: event,
                    message: "Subscription CLI command started",
                    fields: fields
                )
            }
        )
        return try await commandRunner.run(arguments, runtime: runtime)
    }
}
