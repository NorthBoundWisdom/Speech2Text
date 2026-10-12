import Foundation

struct SubscriptionCommandRunner {
    let runner: any ProcessRunning
    let outputHandler: @MainActor (String) -> Void
    let logger: (String, [String: String]) -> Void

    func run(_ arguments: [String], runtime: RuntimeContext) async throws -> String {
        let command = AtotServiceClient.subscriptions(arguments)
        await outputHandler("\n$ \(runtime.cli.path) \(command.joined(separator: " "))\n")
        logger("subscription_command_started", ["subcommand": arguments.first ?? ""])
        let result = try await runner.run(
            executable: runtime.cli,
            arguments: command,
            currentDirectory: runtime.workingDirectory,
            environment: runtime.environment,
            onOutput: outputHandler
        )
        return result.output
    }
}
