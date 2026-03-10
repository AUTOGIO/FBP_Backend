import ArgumentParser
import FBPCLICore
import Foundation

#if canImport(Darwin)
import Darwin
#endif

struct CEPCommand: ParsableCommand {
    static let configuration = CommandConfiguration(
        commandName: "cep",
        abstract: "CEP validation (Brazilian postal code)",
        subcommands: [CEPValidateCommand.self]
    )
}

struct CEPValidateCommand: AsyncParsableCommand {
    static let configuration = CommandConfiguration(
        commandName: "validate",
        abstract: "Validate Brazilian postal code (CEP)"
    )

    @Option(name: .long, help: "FBP base URL")
    var fbpUrl: String?

    @Argument(help: "CEP to validate (8 digits)")
    var cep: String

    @Flag(name: .long, help: "Enrich with coordinates")
    var enrich: Bool = false

    @Flag(name: .long, help: "Output JSON")
    var json: Bool = false

    mutating func run() async throws {
        let baseURL = FBPConfig.baseURL(explicit: fbpUrl)
        let client = FBPApiClient(baseURL: baseURL)

        let request = CEPValidationRequest(cep: cep, enrich: enrich)

        do {
            let response: CEPValidationResponse = try await client.post(path: "/api/utils/cep", body: request)

            if json {
                let encoder = JSONEncoder()
                encoder.outputFormatting = .prettyPrinted
                let data = try encoder.encode(response)
                print(String(data: data, encoding: .utf8)!)
            } else {
                print("success: \(response.success)")
                if let data = response.data {
                    if let v = data.valid { print("valid: \(v)") }
                    if let c = data.cep { print("cep: \(c)") }
                    if let log = data.logradouro { print("logradouro: \(log)") }
                    if let b = data.bairro { print("bairro: \(b)") }
                    if let cid = data.cidade { print("cidade: \(cid)") }
                    if let uf = data.uf { print("uf: \(uf)") }
                }
                if !response.errors.isEmpty {
                    print("errors: \(response.errors.joined(separator: ", "))")
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
