// swift-tools-version: 5.9
import PackageDescription

let package = Package(
    name: "SkullOS",
    platforms: [.macOS(.v13)],
    products: [.executable(name: "SkullOS", targets: ["SkullOS"])],
    targets: [
        .executableTarget(name: "SkullOS", path: "Sources/SkullOS")
    ]
)
