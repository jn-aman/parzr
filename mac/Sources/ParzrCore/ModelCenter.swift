import Combine
import Foundation
import Network

/// The essential model pack's state for every surface (welcome guide, Settings, menu-bar popover, check card), and the
/// policy around it: when a download starts, retries, cancel, remove. Parzr checks with its rules until the pack is ready.
@MainActor
public final class ModelCenter: ObservableObject {
    @Published public private(set) var state: ModelPackState = .missing
    public let pack: ModelPack?
    public let store: ModelStore?
    private let defaults: UserDefaults
    private let development: Bool
    private var download: Task<Void, Never>?
    private var retry: Task<Void, Never>?
    private var failures = 0
    /// Each download's number: a cancelled download that reports late never touches the state of the next one.
    private var generation = 0
    private var monitor: NWPathMonitor?
    private var online = true
    /// Called on the main actor once the pack is ready (the app warms Smart grammar then).
    public var onReady: (() -> Void)?
    /// Retry delays after a failure the download can recover from on its own; the last one repeats.
    public var backoff: [Duration] = [.seconds(30), .seconds(120), .seconds(600), .seconds(1800)]
    static let removedKey = "modelPackRemoved"
    /// Remembers a Remove per pack; the essential pack keeps the key older versions wrote.
    public let removedKey: String

    public init(pack: ModelPack?, store: ModelStore?, defaults: UserDefaults = .standard, development: Bool = false) {
        self.pack = pack; self.store = store; self.defaults = defaults; self.development = development
        removedKey = pack.map { $0.provides["writing_model"] != nil ? Self.removedKey : "\(Self.removedKey).\($0.id)" } ?? Self.removedKey
        refresh()
    }
    /// The app's center: the manifest compiled into the engine, ~/Library/Application Support/Parzr/Models, HTTPS from GitHub.
    /// PARZR_MODEL_PATH or PARZR_GEC_DIR (development) mean the engine uses other files, so nothing is downloaded.
    /// PARZR_MODELS_DIR moves the folder and PARZR_MODELS_BASE_URL replaces the release address (local copies for testing).
    /// `role` picks another pack (the tone pack provides "tone_model"); `developmentVariables` name the variables that point at local files instead.
    public static func live(defaults: UserDefaults = .standard, role: String = "writing_model", developmentVariables: [String] = ["PARZR_MODEL_PATH", "PARZR_GEC_DIR"]) -> ModelCenter {
        let environment = ProcessInfo.processInfo.environment
        let development = developmentVariables.contains { !(environment[$0] ?? "").isEmpty }
        let manifest = WritingEngine.modelManifest().flatMap { try? ModelManifest.decode($0) }
        let pack = role == "writing_model" ? manifest?.essential : manifest?.pack(providing: role)
        var store = ModelStore(root: ModelStore.defaultRoot(environment: environment), transport: URLSessionTransport())
        store.baseURL = environment["PARZR_MODELS_BASE_URL"].flatMap { $0.isEmpty ? nil : URL(string: $0) }
        return ModelCenter(pack: pack, store: store, defaults: defaults, development: development)
    }

    /// The user removed the pack: no automatic download until they ask for it again.
    public var removedByUser: Bool { defaults.bool(forKey: removedKey) }
    public var totalBytes: Int64 { pack?.bytes ?? 0 }
    public var isReady: Bool { state.isReady }

    /// Reads the state from disk (cheap: sizes only). Leaves a running download alone.
    public func refresh() {
        guard !state.isWorking else { return }
        if development { state = .development; return }
        guard let pack, let store else { state = .failed(.other("This copy of Parzr has no model list. Reinstall Parzr.")); return }
        if store.isInstalled(pack) { state = .ready }
        else if case .failed = state {} else { state = .missing }
    }

    /// The automatic download: on a normal launch after the welcome guide, and from its download step. Never after the user removed the pack.
    public func startIfNeeded() {
        refresh()
        guard !removedByUser else { return }
        start()
    }
    /// Starts (or resumes) the download unless the pack is ready or already downloading. `userInitiated` clears an earlier Remove.
    public func start(userInitiated: Bool = false) {
        if userInitiated { defaults.removeObject(forKey: removedKey); failures = 0 }
        refresh()
        guard let pack, let store, !state.isReady, download == nil else { return }
        retry?.cancel(); retry = nil
        state = .downloading(received: store.downloaded(pack), total: pack.bytes)
        generation += 1
        let current = generation
        let gate = ProgressGate { [weak self] next in Task { @MainActor in self?.progress(next, current) } }
        download = Task.detached(priority: .utility) { [weak self] in
            let result = await store.install(pack) { gate.send($0) }
            await self?.finish(result, current)
        }
    }
    /// Stops the download and keeps what arrived, so Download resumes it.
    public func cancel() {
        retry?.cancel(); retry = nil
        download?.cancel(); download = nil; generation += 1
        if state.isWorking { state = .missing }
        defaults.set(true, forKey: removedKey)
    }
    /// Deletes the pack from this Mac. Parzr goes back to the rules alone until the user downloads it again.
    public func remove() {
        cancel()
        guard let pack, let store else { return }
        do { try store.remove(pack); state = .missing } catch { state = .failed(.other("Parzr could not remove the models: \(error.localizedDescription)")) }
        defaults.set(true, forKey: removedKey)
    }
    /// Deletes the pack and downloads it again from scratch.
    public func redownload() {
        retry?.cancel(); retry = nil; download?.cancel(); download = nil; generation += 1
        if let pack, let store { try? store.remove(pack) }
        state = .missing
        start(userInitiated: true)
    }

    private func progress(_ next: ModelPackState, _ number: Int) {
        guard number == generation, download != nil, state.isWorking else { return }
        state = next
    }
    private func finish(_ result: ModelPackState, _ number: Int) {
        guard number == generation else { return }
        download = nil
        switch result {
        case .ready:
            failures = 0; state = .ready; onReady?()
        case .failed(let failure):
            state = result; failures += 1
            if failure.retriesAutomatically && !removedByUser { scheduleRetry(failure) }
        default:
            if state.isWorking { state = .missing }
        }
    }
    private func scheduleRetry(_ failure: ModelPackFailure) {
        retry?.cancel()
        // Offline: the network monitor restarts it the moment a connection returns; the timer is the fallback.
        let delay: Duration = if case .unavailable = failure { .seconds(3600) } else { backoff[min(failures - 1, backoff.count - 1)] }
        retry = Task { [weak self] in
            try? await Task.sleep(for: delay)
            guard !Task.isCancelled else { return }
            self?.retry = nil; self?.start()
        }
    }

    /// Watches for a connection (no traffic: the system reports its path) so a download that failed offline resumes at once.
    public func watchNetwork() {
        guard monitor == nil, !development else { return }
        let monitor = NWPathMonitor(); self.monitor = monitor
        monitor.pathUpdateHandler = { [weak self] path in
            let up = path.status == .satisfied
            Task { @MainActor in self?.networkChanged(up) }
        }
        monitor.start(queue: DispatchQueue(label: "Parzr network path"))
    }
    func networkChanged(_ up: Bool) {
        defer { online = up }
        guard up, !online, case .failed(let failure) = state, failure.retriesAutomatically, !removedByUser else { return }
        start()
    }

    // MARK: Words for the surfaces
    public var sizeText: String { ByteCountFormatter.string(fromByteCount: totalBytes, countStyle: .file) }
    /// One line for Settings and the popover.
    public var statusLine: String {
        switch state {
        case .ready: "Ready. \(sizeText) on this Mac."
        case .development: "Using the models named by PARZR_MODEL_PATH or PARZR_GEC_DIR."
        case .downloading(let received, let total): "Downloading \(ByteCountFormatter.string(fromByteCount: received, countStyle: .file)) of \(ByteCountFormatter.string(fromByteCount: total, countStyle: .file))…"
        case .verifying: "Checking the download…"
        case .missing: removedByUser ? "Not downloaded. Parzr checks with its rules only." : "Not downloaded yet."
        case .failed(let failure): failure.message
        }
    }
    /// What a check says while the pack is not ready (nil once it is): the rules still check everything.
    public var unavailableNote: String? {
        switch state {
        case .ready, .development: nil
        case .downloading, .verifying: "Smart grammar is downloading. Checked with the rules for now."
        case .missing where !removedByUser: "Smart grammar is downloading. Checked with the rules for now."
        case .missing, .failed: "Smart grammar isn't downloaded. Checked with the rules only. Download it in Settings, Models."
        }
    }
    /// Replaces the engine's "model not downloaded" warning with the plain status above; other warnings pass through.
    /// A tone rewrite that could not run says so; the text it returns was corrected by the rules.
    public func explain(_ warnings: [String]?) -> [String]? {
        guard let warnings else { return nil }
        return warnings.map { warning in
            guard warning.contains(Self.engineMissing) else { return warning }
            let waiting = state.isWorking || (state == .missing && !removedByUser)
            if warning.hasPrefix("Kept the corrected text.") { return waiting ? Self.toneWaiting : Self.toneMissing }
            return unavailableNote ?? "Smart grammar is getting ready. Checked with the rules for now."
        }
    }
    public static let toneWaiting = "Tone rewrites use the models Parzr is still downloading. Your text was corrected with the rules."
    public static let toneMissing = "Tone rewrites need the models. Download them in Settings, Models. Your text was corrected with the rules."
    /// Snapshots and previews only: shows a state without downloading anything.
    public func preview(_ state: ModelPackState, removed: Bool = false) {
        generation += 1; download = nil; self.state = state
        if removed { defaults.set(true, forKey: removedKey) } else { defaults.removeObject(forKey: removedKey) }
    }
    /// The pack's models for Settings: one line per top-level item (a file, or a folder such as gector/), with its size, version, license and purpose.
    public var models: [(name: String, bytes: Int64, version: String, license: String, purpose: String)] {
        guard let pack else { return [] }
        var order: [String] = [], groups: [String: [ModelFile]] = [:]
        for file in pack.files {
            let key = String(file.path.split(separator: "/").first ?? "")
            if groups[key] == nil { order.append(key) }
            groups[key, default: []].append(file)
        }
        return order.compactMap { key in
            guard let files = groups[key], let main = files.max(by: { $0.bytes < $1.bytes }) else { return nil }
            return (main.name, files.reduce(0) { $0 + $1.bytes }, main.version, main.license, main.purpose)
        }
    }
    /// The engine's text for a missing writing model (engine/src/model.rs MODEL_MISSING).
    public static let engineMissing = "The writing model is not downloaded yet."
}

/// Passes on at most ten progress updates a second (the download reports every few kilobytes), and every change of kind at once.
final class ProgressGate: @unchecked Sendable {
    private let lock = NSLock()
    private var last = Date.distantPast
    private let forward: @Sendable (ModelPackState) -> Void
    init(_ forward: @escaping @Sendable (ModelPackState) -> Void) { self.forward = forward }
    func send(_ state: ModelPackState) {
        let now = Date()
        let pass: Bool = lock.withLock {
            if case .downloading = state, now.timeIntervalSince(last) < 0.1 { return false }
            last = now; return true
        }
        if pass { forward(state) }
    }
}

