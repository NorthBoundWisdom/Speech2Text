@testable import Audio2TextApp
import Foundation
import XCTest

final class AtotServiceClientTests: XCTestCase {
    func testBuildsTranscribeAndQAFamilyCommands() {
        let audio = URL(fileURLWithPath: "/tmp/input.mp4")
        let output = URL(fileURLWithPath: "/tmp/job")

        XCTAssertEqual(
            serviceMethod(
                AtotServiceClient.transcribe(
                    audioURL: audio,
                    jobDirectory: output
                )
            ),
            "transcribe"
        )
        XCTAssertEqual(serviceParam(AtotServiceClient.transcribe(audioURL: audio, jobDirectory: output), "job_dir") as? String, "/tmp/job")
        XCTAssertEqual(serviceMethod(AtotServiceClient.qa(outputDirectory: output)), "qa")
        XCTAssertEqual(serviceMethod(AtotServiceClient.repair(outputDirectory: output)), "repair")
    }

    func testBuildsImportSubscriptionsAndCloudCommands() {
        let output = URL(fileURLWithPath: "/tmp/output")
        let prompt = URL(fileURLWithPath: "/tmp/prompt.md")

        XCTAssertEqual(
            serviceMethod(
                AtotServiceClient.importXiaoyuzhou(
                    url: "https://www.xiaoyuzhoufm.com/episode/abc",
                    processDirectory: URL(fileURLWithPath: "/tmp/process"),
                    download: false
                )
            ),
            "import_xiaoyuzhou"
        )
        XCTAssertEqual(serviceParam(AtotServiceClient.importXiaoyuzhou(url: "https://www.xiaoyuzhoufm.com/episode/abc", processDirectory: URL(fileURLWithPath: "/tmp/process"), download: false), "download") as? Bool, false)
        XCTAssertEqual(
            serviceMethod(AtotServiceClient.subscriptions(["refresh", "--all", "--json"])),
            "subscriptions"
        )
        XCTAssertEqual(
            serviceParam(AtotServiceClient.subscriptions(["refresh", "--id", "podcast_rss-test", "--full-history", "--json"]), "arguments") as? [String],
            ["refresh", "--id", "podcast_rss-test", "--full-history", "--json"]
        )
        XCTAssertEqual(
            serviceMethod(AtotServiceClient.cloudPrepare(outputDirectory: output, chunkMinutes: "30")),
            "cloud_prepare"
        )
        XCTAssertEqual(
            serviceMethod(AtotServiceClient.cloudSummarize(outputDirectory: output, promptFile: prompt)),
            "cloud_summarize"
        )
        XCTAssertEqual(
            serviceMethod(AtotServiceClient.cloudTitle(outputDirectory: output, promptFile: prompt)),
            "cloud_title"
        )
    }

    func testBuildsReservedSRTCommandWithoutConnectingUI() {
        XCTAssertEqual(
            serviceMethod(
                AtotServiceClient.srt(
                    input: URL(fileURLWithPath: "/tmp/video.mp4"),
                    sourceLanguages: ["en", "zh"],
                    overwrite: true,
                    json: true
                )
            ),
            "srt"
        )
        XCTAssertEqual(serviceParam(AtotServiceClient.srt(input: URL(fileURLWithPath: "/tmp/video.mp4"), sourceLanguages: ["en", "zh"], overwrite: true, json: true), "overwrite") as? Bool, true)
    }

    func testBuildsLocalSRTTranslationCommand() {
        XCTAssertEqual(
            serviceParam(
                AtotServiceClient.srt(
                    input: URL(fileURLWithPath: "/tmp/video.mp4"),
                    sourceLanguages: ["auto"],
                    json: true
                ),
                "languages"
            ) as? [String],
            ["auto"]
        )
    }

    func testBuildsConfigServiceCommands() {
        XCTAssertEqual(serviceMethod(AtotServiceClient.configList()), "config_list")
        XCTAssertEqual(serviceMethod(AtotServiceClient.configInspect()), "config_inspect")
        XCTAssertEqual(serviceMethod(AtotServiceClient.configGet("cloud.model")), "config_get")
        XCTAssertEqual(serviceParam(AtotServiceClient.configGet("cloud.model"), "key") as? String, "cloud.model")
        XCTAssertEqual(serviceMethod(AtotServiceClient.configSet("workflow.default_cloud_summary", value: false)), "config_set")
        XCTAssertEqual(
            serviceParam(AtotServiceClient.configSet("workflow.default_cloud_summary", value: false), "value") as? Bool,
            false
        )
    }

    func testSwiftServiceRequestsConformToSharedContract() throws {
        let audio = URL(fileURLWithPath: "/tmp/input.mp4")
        let output = URL(fileURLWithPath: "/tmp/output")
        let prompt = URL(fileURLWithPath: "/tmp/prompt.md")
        let requests = [
            AtotServiceClient.transcribe(audioURL: audio, jobDirectory: output),
            AtotServiceClient.qa(outputDirectory: output),
            AtotServiceClient.repair(outputDirectory: output),
            AtotServiceClient.importXiaoyuzhou(url: "https://www.xiaoyuzhoufm.com/episode/abc", processDirectory: output, download: false),
            AtotServiceClient.subscriptions(["refresh", "--id", "podcast_rss-test", "--full-history", "--json"]),
            AtotServiceClient.configList(),
            AtotServiceClient.configInspect(),
            AtotServiceClient.configGet("cloud.model"),
            AtotServiceClient.configSet("workflow.default_cloud_summary", value: false),
            AtotServiceClient.cloudPrepare(outputDirectory: output, chunkMinutes: "30"),
            AtotServiceClient.cloudSummarize(outputDirectory: output, promptFile: prompt),
            AtotServiceClient.cloudTitle(outputDirectory: output, promptFile: prompt),
            AtotServiceClient.srt(input: audio, sourceLanguages: ["auto"], overwrite: true, json: true),
        ]
        let contract = try loadServiceContract()
        let declaredSwiftMethods = Set(contract.methods.filter { $0.clients.contains("swift") }.map(\.name))
        let requestMethods = Set(requests.compactMap(serviceMethod))

        XCTAssertEqual(requestMethods, declaredSwiftMethods)
        for request in requests {
            try assertServiceRequest(request, conformsTo: contract)
        }
    }

    func testDecodesConfigInspectionPayload() throws {
        let data = """
        {
          "path": "/tmp/config.toml",
          "effective": {
            "cloud": {"api_key": "***", "timeout": 360, "model_options": ["gpt-5.4-mini"]},
            "local": {"asr_model": "large-v3-turbo"}
          },
          "layers": {
            "built_in_defaults": {"name": "Built-in defaults", "enabled": true, "description": "Defaults"},
            "user_config": {"name": "User config", "enabled": true, "description": "User file", "path": "/tmp/config.toml"}
          },
          "entries": [
            {
              "key": "cloud.api_key",
              "value": "***",
              "redacted": true,
              "source": "user_config",
              "raw_key": "cloud.api_key",
              "editable": true,
              "is_default": false
            }
          ]
        }
        """.data(using: .utf8)!

        let payload = try JSONDecoder().decode(ConfigInspectionPayload.self, from: data)

        XCTAssertEqual(payload.path, "/tmp/config.toml")
        XCTAssertEqual(payload.layers.userConfig.path, "/tmp/config.toml")
        XCTAssertEqual(payload.entries.first?.rawKey, "cloud.api_key")
        XCTAssertEqual(payload.entries.first?.value.displayString, "***")
        XCTAssertEqual(payload.effective["cloud"]?["timeout"]?.displayString, "360")
    }

    private func serviceMethod(_ arguments: [String]) -> String? {
        serviceRequest(arguments)["method"] as? String
    }

    private func serviceParam(_ arguments: [String], _ key: String) -> Any? {
        let request = serviceRequest(arguments)
        let params = request["params"] as? [String: Any]
        return params?[key]
    }

    private func serviceRequest(_ arguments: [String]) -> [String: Any] {
        XCTAssertEqual(arguments.first, "serve")
        XCTAssertTrue(arguments.contains("--stdio"))
        XCTAssertTrue(arguments.contains("--unwrap-result"))
        guard let index = arguments.firstIndex(of: "--request-json") else {
            XCTFail("missing --request-json")
            return [:]
        }
        let data = arguments[index + 1].data(using: .utf8)!
        return (try! JSONSerialization.jsonObject(with: data)) as! [String: Any]
    }

    private func loadServiceContract() throws -> ServiceContract {
        let fileURL = URL(fileURLWithPath: #filePath)
        let repoRoot = fileURL
            .deletingLastPathComponent()
            .deletingLastPathComponent()
            .deletingLastPathComponent()
            .deletingLastPathComponent()
        let contractURL = repoRoot.appendingPathComponent("src/atot/data/service_contract.json")
        let data = try Data(contentsOf: contractURL)
        return try JSONDecoder().decode(ServiceContract.self, from: data)
    }

    private func assertServiceRequest(_ arguments: [String], conformsTo contract: ServiceContract) throws {
        let request = serviceRequest(arguments)
        let method = try XCTUnwrap(request["method"] as? String)
        let spec = try XCTUnwrap(contract.methods.first { $0.name == method })
        let params = request["params"] as? [String: Any] ?? [:]
        let paramSpecs = Dictionary(uniqueKeysWithValues: spec.params.map { ($0.name, $0) })
        let unknownParams = Set(params.keys).subtracting(paramSpecs.keys)

        XCTAssertEqual(unknownParams, [], "Unknown params for \(method): \(unknownParams.sorted())")
        for param in spec.params where param.required == true {
            XCTAssertTrue(params.keys.contains(param.name), "Missing \(method).\(param.name)")
        }
        for (name, value) in params {
            guard let spec = paramSpecs[name] else { continue }
            assertServiceParam(value, matches: spec.type, name: "\(method).\(name)")
            if let minItems = spec.minItems, let values = value as? [Any] {
                XCTAssertGreaterThanOrEqual(values.count, minItems, "\(method).\(name)")
            }
        }
    }

    private func assertServiceParam(_ value: Any, matches type: String, name: String) {
        switch type {
        case "path", "string":
            XCTAssertTrue(value is String, name)
        case "boolean":
            XCTAssertTrue(value is Bool, name)
        case "number":
            XCTAssertTrue(value is NSNumber, name)
            XCTAssertFalse(value is Bool, name)
        case "argv", "path_array", "string_array":
            XCTAssertNotNil(value as? [String], name)
        case "any":
            break
        default:
            XCTFail("Unknown service contract type \(type) for \(name)")
        }
    }
}

private struct ServiceContract: Decodable {
    let methods: [ServiceMethodSpec]
}

private struct ServiceMethodSpec: Decodable {
    let name: String
    let clients: [String]
    let params: [ServiceParamSpec]
}

private struct ServiceParamSpec: Decodable {
    let name: String
    let type: String
    let required: Bool?
    let minItems: Int?

    private enum CodingKeys: String, CodingKey {
        case name
        case type
        case required
        case minItems = "min_items"
    }
}
