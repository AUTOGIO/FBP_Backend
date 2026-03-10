import ArgumentParser
import FBPCLICore
import Foundation

#if canImport(Darwin)
import Darwin
#endif

struct FACCommand: ParsableCommand {
    static let configuration = CommandConfiguration(
        commandName: "fac",
        abstract: "FAC batch processing",
        subcommands: [FACBatchCommand.self, FACStatusCommand.self]
    )
}

struct FACBatchCommand: AsyncParsableCommand {
    static let configuration = CommandConfiguration(
        commandName: "batch",
        abstract: "Process FAC batch from JSON file"
    )

    @Option(name: .long, help: "FBP base URL")
    var fbpUrl: String?

    @Option(name: .shortAndLong, help: "Path to JSON file with facs array")
    var input: String

    @Flag(name: .long, help: "Output JSON")
    var json: Bool = false

    mutating func run() async throws {
        let baseURL = FBPConfig.baseURL(explicit: fbpUrl)
        let client = FBPApiClient(baseURL: baseURL)

        let url = URL(fileURLWithPath: input)
        let fileData = try Data(contentsOf: url)
        let decoded = try JSONDecoder().decode(FACBatchRequest.self, from: fileData)

        do {
            let response: FACBatchResponse = try await client.post(path: "/fac/batch", body: decoded)

            if json {
                let encoder = JSONEncoder()
                encoder.outputFormatting = .prettyPrinted
                let data = try encoder.encode(response)
                print(String(data: data, encoding: .utf8)!)
            } else {
                print("success: \(response.success)")
                print("job_id: \(response.job_id)")
                print("total: \(response.total)")
                print("processed: \(response.processed)")
                if let errs = response.errors, !errs.isEmpty {
                    print("errors: \(errs.joined(separator: ", "))")
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

struct FACStatusCommand: AsyncParsableCommand {
    static let configuration = CommandConfiguration(
        commandName: "status",
        abstract: "Get FAC batch job status"
    )

    @Option(name: .long, help: "FBP base URL")
    var fbpUrl: String?

    @Argument(help: "Job ID")
    var jobId: String

    @Flag(name: .long, help: "Output JSON")
    var json: Bool = false

    mutating func run() async throws {
        let baseURL = FBPConfig.baseURL(explicit: fbpUrl)
        let client = FBPApiClient(baseURL: baseURL)

        struct FACStatusResponse: Codable {
            let success: Bool
            let job_id: String?
            let total: Int?
            let processed: Int?
            let results: [[String: String]]?
            let errors: [String]?
        }

        do {
            let response: FACStatusResponse = try await client.get(path: "/fac/status/\(jobId)")

            if json {
                let encoder = JSONEncoder()
                encoder.outputFormatting = .prettyPrinted
                let data = try encoder.encode(response)
                print(String(data: data, encoding: .utf8)!)
            } else {
                print("success: \(response.success)")
                if let id = response.job_id { print("job_id: \(id)") }
                if let t = response.total { print("total: \(t)") }
                if let p = response.processed { print("processed: \(p)") }
            }
        } catch let e as ApiError {
            exitWithApiError(e)
        } catch {
            print("Error: \(error)", to: &stderrStream)
            Darwin.exit(2)
        }
    }
}
