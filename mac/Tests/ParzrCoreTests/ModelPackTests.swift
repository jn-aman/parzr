import CryptoKit
import XCTest
@testable import ParzrCore

/// A transport that serves bytes from memory and can go offline, cut a download short, ignore ranges or corrupt a file.
final class FakeTransport: ModelTransport, @unchecked Sendable {
    enum Behavior { case serve, offline, notFound, ignoreRange, cutAfter(Int), corrupt, corruptOnce, diskFull, slow }
    private let lock = NSLock()
    private var files: [String: Data] = [:]
    private var behaviors: [String: Behavior] = [:]
    private var corrupted: Set<String> = []
    private(set) var requests: [(name: String, offset: Int64)] = []
    func serve(_ name: String, _ data: Data, _ behavior: Behavior = .serve) { lock.withLock { files[name] = data; behaviors[name] = behavior } }
    func set(_ name: String, _ behavior: Behavior) { lock.withLock { behaviors[name] = behavior } }
    var offsets: [Int64] { lock.withLock { requests.map(\.offset) } }
    func download(_ url: URL, from offset: Int64, into sink: ModelSink) async throws {
        let name = url.lastPathComponent
        let (data, behavior) = lock.withLock { requests.append((name, offset)); return (files[name], behaviors[name] ?? .serve) }
        guard var data else { throw ModelTransportError(.unavailable(status: 404)) }
        switch behavior {
        case .offline: throw URLError(.notConnectedToInternet)
        case .notFound: throw ModelTransportError(.unavailable(status: 404))
        case .diskFull: try sink.write(data.prefix(3)); throw NSError(domain: NSCocoaErrorDomain, code: NSFileWriteOutOfSpaceError)
        case .ignoreRange: if offset > 0 { try sink.restart() }; try sink.write(data); return
        case .corrupt: data[0] ^= 0xFF
        case .corruptOnce: if lock.withLock({ corrupted.insert(name).inserted }) { data[0] ^= 0xFF }
        case .cutAfter(let count):
            set(name, .serve)
            try sink.write(data.subdata(in: Int(offset)..<min(data.count, count))); throw URLError(.networkConnectionLost)
        case .slow:
            for byte in data[Int(offset)...] { try await Task.sleep(for: .milliseconds(20)); try Task.checkCancellation(); try sink.write(Data([byte])) }
            return
        case .serve: break
        }
        try sink.write(data.subdata(in: Int(offset)..<data.count))
    }
}

/// Starts an install and cancels it after `delay`. A free function with an explicit `update` closure: Swift 6.3's
/// region checker on CI could not analyse a `Task` closure in the test class calling `install` with its default argument.
func installThenCancel(_ store: ModelStore, _ pack: ModelPack, after delay: Duration) async -> ModelPackState {
    await withTaskGroup(of: ModelPackState.self) { group in
        group.addTask { await store.install(pack, update: { _ in }) }
        try? await Task.sleep(for: delay)
        group.cancelAll()
        return await group.next() ?? .missing
    }
}

final class ModelPackTests: XCTestCase {
    private var root: URL!
    override func setUp() { root = FileManager.default.temporaryDirectory.appendingPathComponent("parzr-models-\(UUID().uuidString)") }
    override func tearDown() { try? FileManager.default.removeItem(at: root) }

    static func hash(_ data: Data) -> String { SHA256.hash(data: data).map { String(format: "%02x", $0) }.joined() }
    static let model = Data((0..<4000).map { UInt8($0 % 251) }), grammar = Data("grammar weights".utf8), labels = Data("$KEEP\n$DELETE\n".utf8)
    static func file(_ path: String, _ data: Data) -> ModelFile {
        ModelFile(path: path, url: "https://github.com/jn-aman/parzr/releases/download/models-9/" + path.replacingOccurrences(of: "/", with: "."), bytes: Int64(data.count), sha256: hash(data), name: path, version: "test", license: "MIT", purpose: "test")
    }
    static let pack = ModelPack(id: "essential", version: "2", title: "Test", provides: ["writing_model": "writer.gguf", "grammar_model": "gector"],
                                files: [file("writer.gguf", model), file("gector/weights/weight.bin", grammar), file("gector/labels.txt", labels)])
    static func transport(_ behavior: FakeTransport.Behavior = .serve, for name: String = "writer.gguf") -> FakeTransport {
        let fake = FakeTransport()
        fake.serve("writer.gguf", Self.model); fake.serve("gector.weights.weight.bin", Self.grammar); fake.serve("gector.labels.txt", Self.labels)
        fake.set(name, behavior)
        return fake
    }
    func transport(_ behavior: FakeTransport.Behavior = .serve) -> FakeTransport { Self.transport(behavior) }
    func store(_ fake: FakeTransport) -> ModelStore { ModelStore(root: root, transport: fake) }
    var final: URL { root.appendingPathComponent("essential/2") }
    var staging: URL { root.appendingPathComponent("essential/.download-2") }

    func testThePinnedManifestFromTheEngineIsValid() throws {
        guard let data = WritingEngine.modelManifest() else { throw XCTSkip("The engine library is not built here (set PARZR_ENGINE_PATH).") }
        let manifest = try ModelManifest.decode(data)
        let pack = try XCTUnwrap(manifest.essential)
        XCTAssertNotNil(pack.provides["writing_model"]); XCTAssertNotNil(pack.provides["grammar_model"])
        XCTAssertTrue(pack.files.allSatisfy { $0.url.hasPrefix("https://github.com/jn-aman/parzr/releases/download/") })
        XCTAssertTrue(pack.files.allSatisfy { !$0.license.isEmpty && !$0.purpose.isEmpty && !$0.name.isEmpty && !$0.version.isEmpty })
        XCTAssertGreaterThan(pack.bytes, 100_000_000, "the essential pack holds the real models")
        // The slip check is an optional pack of its own, under its own release tag.
        let slips = try XCTUnwrap(manifest.slips)
        XCTAssertNotEqual(slips.id, pack.id)
        XCTAssertEqual(slips.provides["slip_model"], "slips")
        XCTAssertTrue(slips.files.contains { $0.path == "slips/mlm.mlmodelc/weights/weight.bin" })
        XCTAssertTrue(slips.files.allSatisfy { $0.url.contains("/models-slips-\(slips.version)/") })
        XCTAssertLessThan(slips.bytes, 100_000_000)
    }
    func testTheSlipPackIsFoundByItsRole() throws {
        let essential = Self.pack
        let slips = ModelPack(id: "slips", version: "1", provides: ["slip_model": "slips"], files: [Self.file("slips/mlm.bin", Self.grammar)])
        let manifest = ModelManifest(packs: [essential, slips])
        XCTAssertEqual(manifest.essential?.id, "essential")
        XCTAssertEqual(manifest.slips?.id, "slips")
        XCTAssertNil(ModelManifest(packs: [essential]).slips)
    }
    func testManifestRejectsUnsafeEntries() throws {
        func manifest(_ edit: (inout ModelFile) -> Void) -> ModelManifest { var file = Self.file("a.bin", Self.grammar); edit(&file); return ModelManifest(packs: [ModelPack(id: "p", version: "1", files: [file])]) }
        XCTAssertNoThrow(try manifest { _ in }.validate())
        XCTAssertThrowsError(try manifest { $0.path = "/etc/passwd" }.validate())
        XCTAssertThrowsError(try manifest { $0.path = "../outside" }.validate())
        XCTAssertThrowsError(try manifest { $0.path = "gector/.hidden" }.validate())
        XCTAssertThrowsError(try manifest { $0.url = "http://example.com/a.bin" }.validate(), "plain HTTP is refused")
        XCTAssertThrowsError(try manifest { $0.sha256 = "abc" }.validate())
        XCTAssertThrowsError(try manifest { $0.sha256 = String(repeating: "A", count: 64) }.validate())
        XCTAssertThrowsError(try manifest { $0.bytes = 0 }.validate())
        XCTAssertThrowsError(try ModelManifest(schema: 2, packs: []).validate())
        XCTAssertThrowsError(try ModelManifest(packs: [ModelPack(id: "../x", version: "1", files: [])]).validate())
    }
    func testInstallVerifiesMovesIntoPlaceAndRemovesOldVersions() async throws {
        let old = root.appendingPathComponent("essential/1"); try FileManager.default.createDirectory(at: old, withIntermediateDirectories: true)
        let abandoned = root.appendingPathComponent("essential/.download-0"); try FileManager.default.createDirectory(at: abandoned, withIntermediateDirectories: true)
        let fake = transport(), store = store(fake)
        XCTAssertFalse(store.isInstalled(Self.pack))
        let states = Recorder()
        let result = await store.install(Self.pack) { states.add($0) }
        XCTAssertEqual(result, .ready)
        XCTAssertTrue(store.isInstalled(Self.pack))
        XCTAssertEqual(try Data(contentsOf: final.appendingPathComponent("writer.gguf")), Self.model)
        XCTAssertEqual(try Data(contentsOf: final.appendingPathComponent("gector/weights/weight.bin")), Self.grammar)
        XCTAssertTrue(FileManager.default.fileExists(atPath: final.appendingPathComponent("pack.json").path))
        XCTAssertFalse(FileManager.default.fileExists(atPath: staging.path), "the staging folder became the version folder")
        XCTAssertFalse(FileManager.default.fileExists(atPath: old.path), "an older version goes once the new one is verified")
        XCTAssertFalse(FileManager.default.fileExists(atPath: abandoned.path))
        XCTAssertEqual(states.values.last, .verifying)
        XCTAssertTrue(states.values.contains(.downloading(received: 0, total: Self.pack.bytes)))
        // Installed: nothing is downloaded again.
        let again = await store.install(Self.pack)
        XCTAssertEqual(again, .ready); XCTAssertEqual(fake.requests.count, 3)
    }
    func testAFailedVersionNeverReplacesTheInstalledOne() async throws {
        let old = root.appendingPathComponent("essential/1/writer.gguf")
        try FileManager.default.createDirectory(at: old.deletingLastPathComponent(), withIntermediateDirectories: true); try Data("old".utf8).write(to: old)
        let result = await store(transport(.offline)).install(Self.pack)
        XCTAssertEqual(result, .failed(.offline))
        XCTAssertTrue(FileManager.default.fileExists(atPath: old.path), "the old version stays until a new one verifies")
    }
    func testOfflineFailsCleanlyAndKeepsNothingHalfInstalled() async {
        let result = await store(transport(.offline)).install(Self.pack)
        XCTAssertEqual(result, .failed(.offline))
        XCTAssertFalse(FileManager.default.fileExists(atPath: final.path))
        XCTAssertTrue(ModelPackFailure.offline.retriesAutomatically)
    }
    func testAnInterruptedDownloadResumesFromWhereItStopped() async throws {
        let fake = transport(.cutAfter(1500)), store = store(fake)
        let first = await store.install(Self.pack)
        XCTAssertEqual(first, .failed(.offline), "a dropped connection reads as offline")
        XCTAssertEqual(ModelStore.size(staging.appendingPathComponent("writer.gguf.partial")), 1500)
        XCTAssertEqual(store.downloaded(Self.pack), 1500)
        let second = await store.install(Self.pack)
        XCTAssertEqual(second, .ready)
        XCTAssertEqual(fake.requests.filter { $0.name == "writer.gguf" }.map(\.offset), [0, 1500], "the second request asks for the rest only")
        XCTAssertEqual(try Data(contentsOf: final.appendingPathComponent("writer.gguf")), Self.model)
    }
    func testAServerThatIgnoresTheRangeStartsTheFileOver() async throws {
        try FileManager.default.createDirectory(at: staging, withIntermediateDirectories: true)
        try Self.model.prefix(1000).write(to: staging.appendingPathComponent("writer.gguf.partial"))
        let result = await store(transport(.ignoreRange)).install(Self.pack)
        XCTAssertEqual(result, .ready)
        XCTAssertEqual(try Data(contentsOf: final.appendingPathComponent("writer.gguf")), Self.model)
    }
    func testAPartialFileLongerThanTheModelIsDiscarded() async throws {
        try FileManager.default.createDirectory(at: staging, withIntermediateDirectories: true)
        try Data(count: 5000).write(to: staging.appendingPathComponent("writer.gguf.partial"))
        let fake = transport()
        let result = await store(fake).install(Self.pack)
        XCTAssertEqual(result, .ready); XCTAssertEqual(fake.requests.first?.offset, 0)
    }
    func testAHashMismatchIsRetriedOnceThenRefused() async throws {
        let flaky = transport(.corruptOnce)
        let recovered = await store(flaky).install(Self.pack)
        XCTAssertEqual(recovered, .ready, "one damaged download is fetched again from the start")
        XCTAssertEqual(flaky.requests.filter { $0.name == "writer.gguf" }.map(\.offset), [0, 0])
        try FileManager.default.removeItem(at: root)
        let bad = await store(transport(.corrupt)).install(Self.pack)
        XCTAssertEqual(bad, .failed(.corrupt("writer.gguf")))
        XCTAssertFalse(FileManager.default.fileExists(atPath: final.path), "a file that does not match its SHA-256 is never used")
        XCTAssertFalse(FileManager.default.fileExists(atPath: staging.appendingPathComponent("writer.gguf.partial").path), "nor kept for a resume")
        XCTAssertFalse(ModelPackFailure.corrupt("x").retriesAutomatically)
    }
    func testAFullDiskIsReportedBeforeAndDuringTheDownload() async {
        var full = store(transport()); full.freeSpace = { _ in 1000 }
        let before = await full.install(Self.pack)
        guard case .failed(.diskFull(let needed)) = before else { return XCTFail("\(before)") }
        XCTAssertGreaterThan(needed, Self.pack.bytes)
        XCTAssertFalse(FileManager.default.fileExists(atPath: final.path))
        let during = await store(transport(.diskFull)).install(Self.pack)
        guard case .failed(.diskFull) = during else { return XCTFail("\(during)") }
        XCTAssertFalse(FileManager.default.fileExists(atPath: final.path))
        XCTAssertTrue(ModelPackFailure.diskFull(needed: 1).message.contains("free"))
    }
    func testAMissingReleaseIsReportedAsUnavailable() async {
        let result = await store(transport(.notFound)).install(Self.pack)
        XCTAssertEqual(result, .failed(.unavailable(status: 404)))
    }
    func testFailuresFromTheSystemMapToPlainReasons() {
        XCTAssertEqual(ModelStore.failure(for: URLError(.notConnectedToInternet), needed: 1), .offline)
        XCTAssertEqual(ModelStore.failure(for: URLError(.timedOut), needed: 1), .offline)
        XCTAssertEqual(ModelStore.failure(for: NSError(domain: NSPOSIXErrorDomain, code: Int(ENOSPC)), needed: 7), .diskFull(needed: 7))
        XCTAssertEqual(ModelStore.failure(for: NSError(domain: NSCocoaErrorDomain, code: NSFileWriteOutOfSpaceError), needed: 7), .diskFull(needed: 7))
        if case .other = ModelStore.failure(for: NSError(domain: "x", code: 1), needed: 1) {} else { XCTFail() }
    }
    func testCancellingKeepsThePartialFileForLater() async throws {
        let result = await installThenCancel(store(transport(.slow)), Self.pack, after: .milliseconds(300))
        XCTAssertEqual(result, .missing)
        XCTAssertGreaterThan(ModelStore.size(staging.appendingPathComponent("writer.gguf.partial")) ?? 0, 0)
        XCTAssertFalse(FileManager.default.fileExists(atPath: final.path))
    }
    func testRemoveTakesThePackAway() async throws {
        let store = store(transport())
        let installed = await store.install(Self.pack)
        XCTAssertEqual(installed, .ready)
        try store.remove(Self.pack)
        XCTAssertFalse(store.isInstalled(Self.pack)); XCTAssertFalse(FileManager.default.fileExists(atPath: final.path))
        XCTAssertEqual((try? FileManager.default.contentsOfDirectory(atPath: root.appendingPathComponent("essential").path)) ?? [], [])
    }
    func testFileCopiesCanStandInForTheRelease() async throws {
        // A local copy of the pack (file:// URLs): the end-to-end test and development use this, with the same hash checks.
        let assets = root.appendingPathComponent("assets"); try FileManager.default.createDirectory(at: assets, withIntermediateDirectories: true)
        try Self.model.write(to: assets.appendingPathComponent("writer.gguf")); try Self.grammar.write(to: assets.appendingPathComponent("gector.weights.weight.bin")); try Self.labels.write(to: assets.appendingPathComponent("gector.labels.txt"))
        var store = ModelStore(root: root.appendingPathComponent("models"), transport: URLSessionTransport()); store.baseURL = assets
        let result = await store.install(Self.pack)
        XCTAssertEqual(result, .ready)
        XCTAssertEqual(try Data(contentsOf: store.folder(Self.pack).appendingPathComponent("writer.gguf")), Self.model)
        // A wrong copy is refused.
        try Data("tampered".utf8).write(to: assets.appendingPathComponent("gector.labels.txt"))
        try store.remove(Self.pack)
        let tampered = await store.install(Self.pack)
        XCTAssertEqual(tampered, .failed(.corrupt("gector/labels.txt")))
    }
}

final class Recorder: @unchecked Sendable {
    private let lock = NSLock()
    private var states: [ModelPackState] = []
    func add(_ state: ModelPackState) { lock.withLock { states.append(state) } }
    var values: [ModelPackState] { lock.withLock { states } }
}

@MainActor
final class ModelCenterTests: XCTestCase {
    private var root: URL!
    private var defaults: UserDefaults!
    override func setUp() async throws {
        root = FileManager.default.temporaryDirectory.appendingPathComponent("parzr-center-\(UUID().uuidString)")
        defaults = UserDefaults(suiteName: "parzr-center-tests"); defaults.removePersistentDomain(forName: "parzr-center-tests")
    }
    override func tearDown() async throws { try? FileManager.default.removeItem(at: root); defaults.removePersistentDomain(forName: "parzr-center-tests") }
    func center(_ fake: FakeTransport) -> ModelCenter {
        let center = ModelCenter(pack: ModelPackTests.pack, store: ModelStore(root: root, transport: fake), defaults: defaults)
        center.backoff = [.milliseconds(50)]
        return center
    }
    func fake(_ behavior: FakeTransport.Behavior = .serve) -> FakeTransport { ModelPackTests.transport(behavior) }
    func wait(_ center: ModelCenter, for state: ModelPackState, seconds: Double = 5) async {
        for _ in 0..<Int(seconds * 50) where center.state != state { try? await Task.sleep(for: .milliseconds(20)) }
        XCTAssertEqual(center.state, state)
    }

    func testDownloadsReportsAndBecomesReady() async {
        let center = center(fake())
        XCTAssertEqual(center.state, .missing)
        XCTAssertEqual(center.unavailableNote, "Smart grammar is downloading. Checked with the rules for now.")
        var ready = 0; center.onReady = { ready += 1 }
        center.startIfNeeded()
        XCTAssertTrue(center.state.isWorking)
        await wait(center, for: .ready)
        XCTAssertEqual(ready, 1); XCTAssertNil(center.unavailableNote)
        XCTAssertTrue(center.statusLine.hasPrefix("Ready."))
        // A new center (the next launch) finds it on disk without downloading.
        let next = self.center(fake(.offline)); XCTAssertEqual(next.state, .ready)
    }
    func testAFailureRetriesOnItsOwn() async {
        let transport = fake(.cutAfter(10))
        let center = center(transport)
        center.start()
        await wait(center, for: .ready)
        XCTAssertEqual(transport.requests.filter { $0.name == "writer.gguf" }.map(\.offset), [0, 10])
    }
    func testOfflineWaitsForTheConnection() async {
        let transport = fake(.offline)
        let center = center(transport); center.backoff = [.seconds(3600)]
        center.start()
        await wait(center, for: .failed(.offline))
        XCTAssertEqual(center.unavailableNote, "Smart grammar isn't downloaded. Checked with the rules only. Download it in Settings, Models.")
        transport.set("writer.gguf", .serve)
        center.networkChanged(false); center.networkChanged(true)
        await wait(center, for: .ready)
    }
    func testDamagedDownloadsWaitForTheUser() async throws {
        let transport = fake(.corrupt)
        let center = center(transport)
        center.start()
        await wait(center, for: .failed(.corrupt("writer.gguf")))
        try await Task.sleep(for: .milliseconds(300))
        XCTAssertEqual(center.state, .failed(.corrupt("writer.gguf")), "no automatic retry of a damaged file")
        transport.set("writer.gguf", .serve)
        center.start(userInitiated: true)
        await wait(center, for: .ready)
    }
    func testRemoveStopsAutomaticDownloadsUntilAsked() async {
        let center = center(fake())
        center.start(); await wait(center, for: .ready)
        center.remove()
        XCTAssertEqual(center.state, .missing); XCTAssertTrue(center.removedByUser)
        XCTAssertEqual(center.statusLine, "Not downloaded. Parzr checks with its rules only.")
        center.startIfNeeded()
        XCTAssertEqual(center.state, .missing, "the next launch does not download it again")
        center.start(userInitiated: true)
        XCTAssertFalse(center.removedByUser)
        await wait(center, for: .ready)
    }
    func testCancelKeepsProgressAndRedownloadStartsOver() async throws {
        let transport = fake(.slow)
        let center = center(transport)
        center.start()
        try await Task.sleep(for: .milliseconds(200))
        center.cancel()
        XCTAssertEqual(center.state, .missing)
        transport.set("writer.gguf", .serve)
        center.start(userInitiated: true); await wait(center, for: .ready)
        XCTAssertGreaterThan(transport.requests.filter { $0.name == "writer.gguf" }.last?.offset ?? 0, 0, "Download resumed the partial file")
        center.redownload(); await wait(center, for: .ready)
        XCTAssertEqual(transport.requests.filter { $0.name == "writer.gguf" }.last?.offset, 0)
    }
    func testTheSlipPackDownloadsAndIsRemovedOnItsOwn() async {
        let data = Data("slip weights".utf8)
        let pack = ModelPack(id: "slips", version: "1", title: "Word-choice check", provides: ["slip_model": "slips"], files: [ModelPackTests.file("slips/mlm.bin", data)])
        let transport = fake(); transport.serve("slips.mlm.bin", data)
        let essential = center(transport)
        let slips = ModelCenter(pack: pack, store: ModelStore(root: root, transport: transport), defaults: defaults, feature: "Slip check")
        XCTAssertEqual(slips.feature, "Slip check"); XCTAssertEqual(essential.feature, "Smart grammar")
        slips.start(); await wait(slips, for: .ready)
        essential.start(); await wait(essential, for: .ready)
        XCTAssertTrue(FileManager.default.fileExists(atPath: root.appendingPathComponent("slips/1/slips/mlm.bin").path))
        // Removing the slip check leaves the essential pack alone, and its Remove is remembered separately.
        slips.remove()
        XCTAssertTrue(slips.removedByUser); XCTAssertFalse(essential.removedByUser)
        XCTAssertEqual(essential.state, .ready); XCTAssertEqual(slips.state, .missing)
        slips.startIfNeeded(); XCTAssertEqual(slips.state, .missing, "no automatic download after Remove")
        essential.remove(); XCTAssertTrue(essential.removedByUser)
        slips.start(userInitiated: true); XCTAssertFalse(slips.removedByUser); XCTAssertTrue(essential.removedByUser)
        await wait(slips, for: .ready)
    }
    func testDevelopmentModelsNeedNoDownload() {
        let center = ModelCenter(pack: ModelPackTests.pack, store: ModelStore(root: root, transport: fake()), defaults: defaults, development: true)
        XCTAssertEqual(center.state, .development); XCTAssertTrue(center.isReady)
        center.startIfNeeded(); XCTAssertEqual(center.state, .development)
    }
    func testWithoutAManifestNothingDownloadsAndTheRulesStillWork() {
        let center = ModelCenter(pack: nil, store: nil, defaults: defaults)
        center.startIfNeeded()
        guard case .failed = center.state else { return XCTFail("\(center.state)") }
        XCTAssertNotNil(center.unavailableNote)
    }
    func testTheEngineWarningBecomesAPlainNote() {
        let center = center(fake())
        XCTAssertEqual(center.explain(["Grammar checked; context refinement unavailable. \(ModelCenter.engineMissing)", "other"]), ["Smart grammar is downloading. Checked with the rules for now.", "other"])
        XCTAssertEqual(center.explain(["context.pending"]), ["context.pending"])
        XCTAssertEqual(center.explain(["Kept the corrected text. \(ModelCenter.engineMissing)"]), [ModelCenter.toneWaiting])
        let empty = EmptyCheck(mode: .professional, status: ModelCenter.toneWaiting)
        XCTAssertEqual(empty.title, "Professional needs the models"); XCTAssertTrue(empty.warning)
        center.remove()
        XCTAssertEqual(center.explain(["Kept the corrected text. \(ModelCenter.engineMissing)"]), [ModelCenter.toneMissing])
        XCTAssertEqual(center.models.map(\.name), ["writer.gguf", "gector/weights/weight.bin"])
        XCTAssertNil(center.explain(nil))
    }
}
