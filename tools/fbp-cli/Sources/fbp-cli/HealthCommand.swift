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
        let baseURL = FBPConfig.baseURL(explicit: fbpUrl)
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
        } catch let e as ApiError {
            exitWithApiError(e)
        } catch {
            print("Error: \(error)", to: &stderrStream)
            Darwin.exit(2)
        }
    }
}
