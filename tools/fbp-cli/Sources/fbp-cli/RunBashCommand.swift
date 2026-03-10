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
        let baseURL = FBPConfig.baseURL(explicit: fbpUrl)
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
                // Propagate script exit code so automation can detect failure
                Darwin.exit(response.success ? 0 : Int32(response.exit_code))
            } else {
                if !response.stdout.isEmpty { print(response.stdout) }
                if !response.stderr.isEmpty { print(response.stderr, to: &stderrStream) }
                Darwin.exit(response.success ? 0 : Int32(response.exit_code))
            }
        } catch let e as ApiError {
            exitWithApiError(e)
        } catch {
            print("Error: \(error)", to: &stderrStream)
            Darwin.exit(2)
        }
    }
}
