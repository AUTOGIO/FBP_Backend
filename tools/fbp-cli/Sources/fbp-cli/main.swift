import ArgumentParser
import FBPCLICore

@main
struct FBPCli: AsyncParsableCommand {
    static let configuration = CommandConfiguration(
        commandName: "fbp",
        abstract: "FBP/FoKS automation CLI - native Swift client for FBP Backend",
        discussion: """
            Requires FBP Backend running (default: http://127.0.0.1:8000).
            Set FBP_BASE_URL or use --fbp-url to override.
            """,
        version: "0.2.0",
        subcommands: [
            HealthCommand.self,
            NFACommand.self,
            RedesimCommand.self,
            FACCommand.self,
            CEPCommand.self,
            RunBashCommand.self,
            MetricsCommand.self,
        ],
        defaultSubcommand: HealthCommand.self
    )
}
