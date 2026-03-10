import Foundation

/// Central configuration for FBP CLI. No config file; env and explicit option only.
public enum FBPConfig {
    /// Default base URL when no env or option is set.
    public static let defaultBaseURL = "http://127.0.0.1:8000"

    /// Resolves backend base URL: explicit override → FBP_BASE_URL env → default.
    /// - Parameter explicitURL: Per-command `--fbp-url` (or nil).
    /// - Returns: Normalized base URL (no trailing slash).
    public static func baseURL(explicit explicitURL: String?) -> String {
        let raw = explicitURL
            ?? ProcessInfo.processInfo.environment["FBP_BASE_URL"]
            ?? defaultBaseURL
        return raw.hasSuffix("/") ? String(raw.dropLast()) : raw
    }
}
