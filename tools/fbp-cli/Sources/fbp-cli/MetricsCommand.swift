import ArgumentParser
import FBPCLICore
import Foundation

#if canImport(Darwin)
import Darwin
#endif

struct MetricsCommand: AsyncParsableCommand {
    static let configuration = CommandConfiguration(
        commandName: "metrics",
        abstract: "Get FBP system metrics"
    )

    @Option(name: .long, help: "FBP base URL")
    var fbpUrl: String?

    @Flag(name: .long, help: "Output JSON")
    var json: Bool = false

    mutating func run() async throws {
        let baseURL = FBPConfig.baseURL(explicit: fbpUrl)
        let client = FBPApiClient(baseURL: baseURL)

        do {
            let data = try await client.getData(path: "/metrics")
            let raw = try JSONSerialization.jsonObject(with: data)

            if json {
                let out = try JSONSerialization.data(withJSONObject: raw)
                print(String(data: out, encoding: .utf8)!)
            } else {
                if let dict = raw as? [String: Any] {
                    for (k, v) in dict.sorted(by: { $0.key < $1.key }) {
                        print("\(k): \(v)")
                    }
                } else {
                    print(raw)
                }
            }
        } catch let e as ApiError {
            exitWithApiError(e)
        } catch {
            print("Error: \(error)", to: &stderrStream)
            Darwin.exit(2)
        }
    }
}
