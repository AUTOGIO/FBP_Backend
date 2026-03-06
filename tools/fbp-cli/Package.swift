// swift-tools-version: 5.9
import PackageDescription

let package = Package(
    name: "fbp-cli",
    platforms: [
        .macOS(.v13),
    ],
    products: [
        .executable(name: "fbp", targets: ["fbp-cli"]),
    ],
    dependencies: [
        .package(url: "https://github.com/apple/swift-argument-parser", from: "1.2.0"),
    ],
    targets: [
        .executableTarget(
            name: "fbp-cli",
            dependencies: [
                "FBPCLICore",
                .product(name: "ArgumentParser", package: "swift-argument-parser"),
            ],
            swiftSettings: [.unsafeFlags(["-parse-as-library"])]
        ),
        .target(
            name: "FBPCLICore",
            dependencies: []
        ),
        .testTarget(
            name: "FBPCLITests",
            dependencies: ["FBPCLICore"],
            path: "Tests/FBPCLITests"
        ),
    ]
)
