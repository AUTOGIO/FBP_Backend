import ArgumentParser
import FBPCLICore
import Foundation

#if canImport(Darwin)
import Darwin
#endif

struct RunBashCommand: AsyncParsableCommand {
    static let configuration = CommandConfiguration(
        commandName: "run-bash",
        abstract: "Execute bash script via FBP executor"
    )

    @Option(name: .long, help: "FBP base URL")
    var fbpUrl: String?

    @Option(name: .shortAndLong, help: "Path to script file (or use stdin)")
    var file: String?

    @Option(name: .shortAndLong, help: "Timeout in seconds")
    var timeout: Int = 60

    @Flag(name: .long, help: "Output JSON")
    var json: Bool = false

    mutating func run() async throws {
        let baseURL = fbpUrl ?? ProcessInfo.processInfo.environment["FBP_BASE_URL"] ?? "http://127.0.0.1:8000"
        let client = FBPApiClient(baseURL: baseURL)

        let scriptContent: String
        if let path = file {
            let url = URL(fileURLWithPath: path)
            scriptContent = try String(contentsOf: url)
        } else {
            scriptContent = String(data: FileHandle.standardInput.readDataToEndOfFile(), encoding: .utf8) ?? ""
        }

        guard !scriptContent.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty else {
            print("Error: No script content (use --file or stdin)", to: &stderrStream)
            Darwin.exit(1)
        }

        let request = ScriptExecutionRequest(script_content: scriptContent, timeout: timeout)

        do {
            let response: ScriptExecutionResponse = try await client.post(path: "/api/executor/run-bash", body: request)

            if json {
                let encoder = JSONEncoder()
                encoder.outputFormatting = .prettyPrinted
                let data = try encoder.encode(response)
                print(String(data: data, encoding: .utf8)!)
            } else {
                if !response.stdout.isEmpty { print(response.stdout) }
                if !response.stderr.isEmpty { print(response.stderr, to: &stderrStream) }
                if response.success {
                    Darwin.exit(0)
                } else {
                    Darwin.exit(Int32(response.exit_code))
                }
            }
        } catch ApiError.requestFailed(let code, let body) {
            print("Error: FBP returned status \(code)", to: &stderrStream)
            if let body = body { print(body, to: &stderrStream) }
            Darwin.exit(2)
        } catch {
            print("Error: \(error)", to: &stderrStream)
            Darwin.exit(2)
        }
    }
}
