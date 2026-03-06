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
