import ArgumentParser
import FBPCLICore
import Foundation

#if canImport(Darwin)
import Darwin
#endif

struct HealthCommand: AsyncParsableCommand {
    static let configuration = CommandConfiguration(
        commandName: "health",
        abstract: "Check FBP backend health"
    )

    @Option(name: .long, help: "FBP base URL")
    var fbpUrl: String?

    @Flag(name: .long, help: "Output JSON")
    var json: Bool = false

    mutating func run() async throws {
        let baseURL = fbpUrl ?? ProcessInfo.processInfo.environment["FBP_BASE_URL"] ?? "http://127.0.0.1:8000"
        let client = FBPApiClient(baseURL: baseURL)

        do {
            let response: HealthResponse = try await client.get(path: "/health")

            if json {
                let encoder = JSONEncoder()
                encoder.outputFormatting = .prettyPrinted
                let data = try encoder.encode(response)
                print(String(data: data, encoding: .utf8)!)
            } else {
                print("FBP Backend: \(response.status)")
                if let machine = response.machine { print("Machine: \(machine)") }
                if let project = response.project { print("Project: \(project)") }
            }
        } catch ApiError.requestFailed(let code, let body) {
            print("Error: FBP returned status \(code)", to: &stderrStream)
            if let body = body { print(body, to: &stderrStream) }
            Darwin.exit(2)
        } catch ApiError.networkError(let err) {
            print("Error: \(err.localizedDescription)", to: &stderrStream)
            Darwin.exit(2)
        } catch {
            print("Error: \(error)", to: &stderrStream)
            Darwin.exit(2)
        }
    }
}
