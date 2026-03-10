import ArgumentParser
import FBPCLICore
import Foundation

#if canImport(Darwin)
import Darwin
#endif

struct NFACommand: ParsableCommand {
    static let configuration = CommandConfiguration(
        commandName: "nfa",
        abstract: "NFA automation (consultation, status)",
        subcommands: [NFAConsultCommand.self, NFAStatusCommand.self]
    )
}

struct NFAConsultCommand: AsyncParsableCommand {
    static let configuration = CommandConfiguration(
        commandName: "consult",
        abstract: "Create NFA consultation job"
    )

    @Option(name: .long, help: "FBP base URL")
    var fbpUrl: String?

    @Option(name: .shortAndLong, help: "Data inicial (DD/MM/YYYY)")
    var from: String

    @Option(name: .shortAndLong, help: "Data final (DD/MM/YYYY)")
    var to: String

    @Option(name: .shortAndLong, help: "Matrícula")
    var matricula: String = "1595504"

    @Flag(name: .long, help: "Output JSON")
    var json: Bool = false

    mutating func run() async throws {
        let baseURL = FBPConfig.baseURL(explicit: fbpUrl)
        let client = FBPApiClient(baseURL: baseURL)

        let request = NFAConsultRequest(
            data_inicial: from,
            data_final: to,
            matricula: matricula,
            username: nil,
            password: nil
        )

        do {
            let response: NFAConsultResponse = try await client.post(path: "/nfa/consult", body: request)

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

struct NFAStatusCommand: AsyncParsableCommand {
    static let configuration = CommandConfiguration(
        commandName: "status",
        abstract: "Get NFA consultation job status"
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

        func fetch() async throws -> NFAJobStatusResponse {
            try await client.get(path: "/nfa/consult/status/\(jobId)")
        }

        do {
            var response: NFAJobStatusResponse = try await fetch()
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
                if let nfa = response.nfa_numero { print("nfa_numero: \(nfa)") }
                if let danfe = response.danfe_path { print("danfe_path: \(danfe)") }
                if let dar = response.dar_path { print("dar_path: \(dar)") }
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
