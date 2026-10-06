// swift-tools-version: 6.0
import PackageDescription
let package = Package(
    name: "parzr", platforms: [.macOS(.v13)],
    products: [.executable(name: "parzr", targets: ["Parzr"]), .library(name: "ParzrCore", targets: ["ParzrCore"])],
    dependencies: [.package(url: "https://github.com/EmergeTools/Pow", exact: "1.0.6"), .package(url: "https://github.com/sparkle-project/Sparkle", exact: "2.9.5")],
    targets: [.target(name: "ParzrCore"), .executableTarget(name: "Parzr", dependencies: ["ParzrCore", .product(name: "Pow", package: "Pow"), .product(name: "Sparkle", package: "Sparkle")]), .executableTarget(name: "ParzrFixture"), .testTarget(name: "ParzrCoreTests", dependencies: ["ParzrCore"]), .testTarget(name: "ParzrAppTests", dependencies: ["Parzr", "ParzrCore"])]
)
