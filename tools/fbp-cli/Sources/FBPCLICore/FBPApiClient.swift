import Foundation

public enum ApiError: Error {
    case invalidURL
    case requestFailed(statusCode: Int, body: String?)
    case networkError(Error)
    case decodeError(Error)
    case timeout
}

public struct FBPApiClient {
    public static let defaultTimeout: TimeInterval = 30

    private let baseURL: String
    private let session: URLSession

    /// - Parameters:
    ///   - baseURL: Resolved backend base URL (e.g. from `FBPConfig.baseURL(explicit:)`).
    ///   - timeout: Request timeout in seconds; default 30.
    public init(baseURL: String, timeout: TimeInterval = defaultTimeout) {
        self.baseURL = baseURL.hasSuffix("/") ? String(baseURL.dropLast()) : baseURL
        let config = URLSessionConfiguration.default
        config.timeoutIntervalForRequest = timeout
        config.timeoutIntervalForResource = timeout
        self.session = URLSession(configuration: config)
    }

    private func url(path: String) -> URL? {
        URL(string: baseURL + path)
    }

    public func get<T: Decodable>(path: String) async throws -> T {
        let data = try await getData(path: path)
        do {
            return try JSONDecoder().decode(T.self, from: data)
        } catch {
            throw ApiError.decodeError(error)
        }
    }

    public func getData(path: String) async throws -> Data {
        guard let requestURL = url(path: path) else { throw ApiError.invalidURL }

        let (data, response): (Data, URLResponse)
        do {
            (data, response) = try await session.data(from: requestURL)
        } catch let urlError as URLError where urlError.code == .timedOut {
            throw ApiError.timeout
        } catch {
            throw ApiError.networkError(error)
        }

        guard let http = response as? HTTPURLResponse else {
            throw ApiError.networkError(NSError(domain: "FBPApiClient", code: -1, userInfo: [NSLocalizedDescriptionKey: "Invalid response"]))
        }

        guard (200...299).contains(http.statusCode) else {
            let body = String(data: data, encoding: .utf8)
            throw ApiError.requestFailed(statusCode: http.statusCode, body: body)
        }

        return data
    }

    public func post<T: Decodable, B: Encodable>(path: String, body: B) async throws -> T {
        guard let requestURL = url(path: path) else { throw ApiError.invalidURL }

        var request = URLRequest(url: requestURL)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = try JSONEncoder().encode(body)

        let (data, response): (Data, URLResponse)
        do {
            (data, response) = try await session.data(for: request)
        } catch let urlError as URLError where urlError.code == .timedOut {
            throw ApiError.timeout
        } catch {
            throw ApiError.networkError(error)
        }

        guard let http = response as? HTTPURLResponse else {
            throw ApiError.networkError(NSError(domain: "FBPApiClient", code: -1, userInfo: [NSLocalizedDescriptionKey: "Invalid response"]))
        }

        guard (200...299).contains(http.statusCode) else {
            let bodyStr = String(data: data, encoding: .utf8)
            throw ApiError.requestFailed(statusCode: http.statusCode, body: bodyStr)
        }

        do {
            return try JSONDecoder().decode(T.self, from: data)
        } catch {
            throw ApiError.decodeError(error)
        }
    }

    public func post(path: String, body: [String: Any]) async throws -> Data {
        guard let requestURL = url(path: path) else { throw ApiError.invalidURL }

        var request = URLRequest(url: requestURL)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = try JSONSerialization.data(withJSONObject: body)

        let (data, response): (Data, URLResponse)
        do {
            (data, response) = try await session.data(for: request)
        } catch let urlError as URLError where urlError.code == .timedOut {
            throw ApiError.timeout
        } catch {
            throw ApiError.networkError(error)
        }

        guard let http = response as? HTTPURLResponse else {
            throw ApiError.networkError(NSError(domain: "FBPApiClient", code: -1, userInfo: [NSLocalizedDescriptionKey: "Invalid response"]))
        }

        guard (200...299).contains(http.statusCode) else {
            let bodyStr = String(data: data, encoding: .utf8)
            throw ApiError.requestFailed(statusCode: http.statusCode, body: bodyStr)
        }

        return data
    }
}
