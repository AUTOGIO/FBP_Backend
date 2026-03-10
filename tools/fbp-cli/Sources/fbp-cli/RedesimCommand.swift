import ArgumentParser
import FBPCLICore
import Foundation

#if canImport(Darwin)
import Darwin
#endif

struct RedesimCommand: ParsableCommand {
    static let configuration = CommandConfiguration(
        commandName: "redesim",
        abstract: "REDESIM consulta (create job, status)",
        subcommands: [RedesimConsultaCommand.self, RedesimStatusCommand.self]
    )
}

struct RedesimConsultaCommand: AsyncParsableCommand {
    static let configuration = CommandConfiguration(
        commandName: "consulta",
        abstract: "Create REDESIM consulta job"
    )

    @Option(name: .long, help: "FBP base URL")
    var fbpUrl: String?

    @Option(name: .long, help: "Data início (DD/MM/YYYY)")
    var from: String?

    @Option(name: .long, help: "Data fim (DD/MM/YYYY)")
    var to: String?

    @Flag(name: .long, help: "Output JSON")
    var json: Bool = false

    mutating func run() async throws {
        let baseURL = FBPConfig.baseURL(explicit: fbpUrl)
        let client = FBPApiClient(baseURL: baseURL)

        let request = CadRedesimConsultaRequest(
            data_criacao_inicio: from,
            data_criacao_fim: to,
            wait_user_dates: true,
            username: nil,
            password: nil
        )

        do {
            let response: CadRedesimConsultaResponse = try await client.post(path: "/cad/redesim/consulta", body: request)

            if json {
                let encoder = JSONEncoder()
                encoder.outputFormatting = .prettyPrinted
                let data = try encoder.encode(response)
                print(String(data: data, encoding: .utf8)!)
            } else {
                print("job_id: \(response.job_id)")
                print("status: \(response.status)")
            }
        } catch let e as ApiError {
            exitWithApiError(e)
        } catch {
            print("Error: \(error)", to: &stderrStream)
            Darwin.exit(2)
        }
    }
}

struct RedesimStatusCommand: AsyncParsableCommand {
    static let configuration = CommandConfiguration(
        commandName: "status",
        abstract: "Get REDESIM consulta job status"
    )

    @Option(name: .long, help: "FBP base URL")
    var fbpUrl: String?

    @Argument(help: "Job ID")
    var jobId: String

    @Flag(name: .long, help: "Poll until completed or failed (max 5 min)")
    var wait: Bool = false

    @Flag(name: .long, help: "Output JSON")
    var json: Bool = false

    mutating func run() async throws {
        let baseURL = FBPConfig.baseURL(explicit: fbpUrl)
        let client = FBPApiClient(baseURL: baseURL)

        func fetch() async throws -> CadRedesimJobStatusResponse {
            try await client.get(path: "/cad/redesim/consulta/status/\(jobId)")
        }

        do {
            var response: CadRedesimJobStatusResponse = try await fetch()
            if wait {
                let deadline = Date().addingTimeInterval(300)
                while !["completed", "failed"].contains(response.status) && Date() < deadline {
                    try await Task.sleep(nanoseconds: 3_000_000_000)
                    response = try await fetch()
                }
            }

            if json {
                let encoder = JSONEncoder()
                encoder.outputFormatting = .prettyPrinted
                let data = try encoder.encode(response)
                print(String(data: data, encoding: .utf8)!)
            } else {
                print("job_id: \(response.job_id)")
                print("status: \(response.status)")
                if let err = response.error { print("error: \(err)") }
            }
        } catch let e as ApiError {
            exitWithApiError(e)
        } catch {
            print("Error: \(error)", to: &stderrStream)
            Darwin.exit(2)
        }
    }
}
