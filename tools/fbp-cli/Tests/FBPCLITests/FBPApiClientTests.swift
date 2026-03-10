import XCTest
@testable import FBPCLICore

final class FBPApiClientTests: XCTestCase {
    func testClientInitWithDefaultURL() {
        let _ = FBPApiClient(baseURL: FBPConfig.defaultBaseURL)
    }

    func testClientInitWithCustomURL() {
        let _ = FBPApiClient(baseURL: "http://localhost:9000")
    }

    func testGetDataThrowsInvalidURLForBadBaseURL() async {
        let client = FBPApiClient(baseURL: "not a valid url")
        do {
            _ = try await client.getData(path: "/health")
            XCTFail("Expected URL construction/request error")
        } catch let error as ApiError {
            switch error {
            case .invalidURL:
                break
            case .networkError:
                break
            default:
                XCTFail("Expected invalidURL/networkError but got \(error)")
            }
        } catch is URLError {
            // URLSession may surface unsupported URL directly as URLError.
            XCTAssertTrue(true)
        } catch {
            XCTFail("Expected ApiError.invalidURL or ApiError.networkError but got \(error)")
        }
    }

    func testConfigBaseURLUsesEnvironmentWhenExplicitNil() async {
        setenv("FBP_BASE_URL", "invalid base url", 1)
        defer { unsetenv("FBP_BASE_URL") }

        let baseURL = FBPConfig.baseURL(explicit: nil)
        XCTAssertEqual(baseURL, "invalid base url")

        let client = FBPApiClient(baseURL: baseURL)
        do {
            _ = try await client.getData(path: "/health")
            XCTFail("Expected URL construction/request error from environment base URL")
        } catch let error as ApiError {
            switch error {
            case .invalidURL:
                break
            case .networkError:
                break
            default:
                XCTFail("Expected invalidURL/networkError but got \(error)")
            }
        } catch is URLError {
            // URLSession may surface unsupported URL directly as URLError.
            XCTAssertTrue(true)
        } catch {
            XCTFail("Expected ApiError.invalidURL or ApiError.networkError but got \(error)")
        }
    }

    func testConfigBaseURLExplicitOverridesEnv() {
        setenv("FBP_BASE_URL", "http://env:8000", 1)
        defer { unsetenv("FBP_BASE_URL") }
        XCTAssertEqual(FBPConfig.baseURL(explicit: "http://override:9000"), "http://override:9000")
    }

    func testConfigBaseURLStripsTrailingSlash() {
        XCTAssertEqual(FBPConfig.baseURL(explicit: "http://localhost:8000/"), "http://localhost:8000")
    }
}
