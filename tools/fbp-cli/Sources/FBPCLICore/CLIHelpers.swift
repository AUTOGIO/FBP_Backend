import Foundation

#if canImport(Darwin)
import Darwin
#else
import Glibc
#endif

public struct StderrStream: TextOutputStream {
    public init() {}

    public mutating func write(_ string: String) {
        fputs(string, stderr)
    }
}

public var stderrStream = StderrStream()

public func fail(_ message: String) -> Never {
    print(message, to: &stderrStream)
    exit(2)
}

/// Print user-facing message for `ApiError` and exit with code 2. Use from commands for consistent UX.
public func exitWithApiError(_ error: ApiError) -> Never {
    switch error {
    case .invalidURL:
        print("Error: Invalid backend URL.", to: &stderrStream)
    case .requestFailed(let code, let body):
        print("Error: FBP returned status \(code).", to: &stderrStream)
        if let body = body, !body.isEmpty { print(body, to: &stderrStream) }
    case .networkError(let err):
        if let urlErr = err as? URLError, urlErr.code == .cannotConnectToHost {
            print("Error: Cannot reach FBP backend. Is it running at the configured URL?", to: &stderrStream)
        } else {
            print("Error: \(err.localizedDescription)", to: &stderrStream)
        }
    case .decodeError(let err):
        print("Error: Invalid response from backend: \(err.localizedDescription)", to: &stderrStream)
    case .timeout:
        print("Error: Request timed out. Backend may be slow or unreachable.", to: &stderrStream)
    }
    exit(2)
}
