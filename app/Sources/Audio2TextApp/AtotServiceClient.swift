import Foundation

enum AtotServiceClient {
    static func transcribe(
        audioURL: URL,
        jobDirectory: URL,
        localOnly: Bool = true
    ) -> [String] {
        serviceArguments(
            method: "transcribe",
            params: [
                "input": audioURL.path,
                "job_dir": jobDirectory.path,
                "local_only": localOnly,
            ]
        )
    }

    static func qa(outputDirectory: URL) -> [String] {
        serviceArguments(method: "qa", params: ["output": outputDirectory.path])
    }

    static func repair(outputDirectory: URL, localOnly: Bool = true) -> [String] {
        serviceArguments(
            method: "repair",
            params: [
                "output": outputDirectory.path,
                "local_only": localOnly,
            ]
        )
    }

    static func importXiaoyuzhou(
        url: String,
        processDirectory: URL,
        download: Bool,
        json _: Bool = true
    ) -> [String] {
        serviceArguments(
            method: "import_xiaoyuzhou",
            params: [
                "url": url,
                "process_dir": processDirectory.path,
                "download": download,
                "data_only": true,
                "transcribe": false,
            ]
        )
    }

    static func subscriptions(_ arguments: [String]) -> [String] {
        serviceArguments(method: "subscriptions", params: ["arguments": arguments])
    }

    static func configList() -> [String] {
        serviceArguments(method: "config_list", params: [:])
    }

    static func configInspect() -> [String] {
        serviceArguments(method: "config_inspect", params: [:])
    }

    static func configGet(_ key: String) -> [String] {
        serviceArguments(method: "config_get", params: ["key": key])
    }

    static func configSet(_ key: String, value: Any) -> [String] {
        serviceArguments(method: "config_set", params: ["key": key, "value": value])
    }

    static func cloudPrepare(outputDirectory: URL, chunkMinutes: String) -> [String] {
        serviceArguments(
            method: "cloud_prepare",
            params: [
                "output": outputDirectory.path,
                "chunk_minutes": Double(chunkMinutes) ?? 20.0,
            ]
        )
    }

    static func cloudSummarize(
        outputDirectory: URL,
        promptFile: URL,
        mode: String = "chunked"
    ) -> [String] {
        serviceArguments(
            method: "cloud_summarize",
            params: [
                "output": outputDirectory.path,
                "call_api": true,
                "prompt_file": promptFile.path,
                "mode": mode,
            ]
        )
    }

    static func cloudTitle(
        outputDirectory: URL,
        promptFile: URL,
        force: Bool = true
    ) -> [String] {
        serviceArguments(
            method: "cloud_title",
            params: [
                "output": outputDirectory.path,
                "call_api": true,
                "prompt_file": promptFile.path,
                "force": force,
            ]
        )
    }

    static func srt(
        input: URL,
        sourceLanguages: [String],
        overwrite: Bool = false,
        json _: Bool = false
    ) -> [String] {
        serviceArguments(
            method: "srt",
            params: [
                "inputs": [input.path],
                "languages": sourceLanguages,
                "overwrite": overwrite,
            ]
        )
    }

    private static func serviceArguments(method: String, params: [String: Any]) -> [String] {
        let request: [String: Any] = [
            "method": method,
            "params": params,
        ]
        let data = try! JSONSerialization.data(withJSONObject: request, options: [.sortedKeys])
        let text = String(data: data, encoding: .utf8)!
        return [
            "serve",
            "--stdio",
            "--request-json",
            text,
            "--unwrap-result",
        ]
    }
}
