// swift-tools-version: 5.9

import PackageDescription

let package = Package(
    name: "Audio2TextApp",
    platforms: [
        .macOS(.v13),
        .iOS(.v17),
    ],
    products: [
        .library(name: "Audio2TextCore", targets: ["Audio2TextCore"]),
        .executable(name: "Audio2TextApp", targets: ["Audio2TextApp"]),
    ],
    targets: [
        .target(
            name: "Audio2TextCore",
            path: "Sources/Audio2TextCore"
        ),
        .executableTarget(
            name: "Audio2TextApp",
            dependencies: ["Audio2TextCore"],
            path: "Sources/Audio2TextApp"
        ),
        .testTarget(
            name: "Audio2TextAppTests",
            dependencies: ["Audio2TextApp"],
            path: "Tests/Audio2TextAppTests"
        ),
        .testTarget(
            name: "Audio2TextCoreTests",
            dependencies: ["Audio2TextCore"],
            path: "Tests/Audio2TextCoreTests",
            resources: [.copy("Fixtures")]
        ),
    ]
)
