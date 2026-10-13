import CryptoKit
import Darwin
import Foundation

// Model packs: the model files Parzr downloads on demand instead of shipping them in the app.
// The pinned manifest is compiled into the engine (engine/models.json) and read through `parzr_model_manifest`.
// A pack is staged in `<root>/<pack>/.download-<version>/` (each file as `<name>.partial`, resumed with a Range
// request, then checked against its SHA-256 and renamed), and the folder is renamed to `<root>/<pack>/<version>/`
// only when every file is verified: the engine treats an existing version folder as complete.

public struct ModelFile: Codable, Equatable, Sendable {
    public var path: String
    public var url: String
    public var bytes: Int64
    public var sha256: String
    public var name: String
    public var version: String
    public var license: String
    public var purpose: String
    public init(path: String, url: String, bytes: Int64, sha256: String, name: String = "", version: String = "", license: String = "", purpose: String = "") {
        self.path = path; self.url = url; self.bytes = bytes; self.sha256 = sha256; self.name = name; self.version = version; self.license = license; self.purpose = purpose
    }
}

public struct ModelPack: Codable, Equatable, Sendable, Identifiable {
    public var id: String
    public var version: String
    public var title: String
    public var purpose: String
    public var license: String
    public var provides: [String: String]
    public var files: [ModelFile]
    public var bytes: Int64 { files.reduce(0) { $0 + $1.bytes } }
    public init(id: String, version: String, title: String = "", purpose: String = "", license: String = "", provides: [String: String] = [:], files: [ModelFile]) {
        self.id = id; self.version = version; self.title = title; self.purpose = purpose; self.license = license; self.provides = provides; self.files = files
    }
}

public struct ModelManifest: Codable, Equatable, Sendable {
    public var schema: Int
    public var packs: [ModelPack]
    public init(schema: Int = 1, packs: [ModelPack]) { self.schema = schema; self.packs = packs }
    /// Parses and checks a manifest: known schema, safe relative paths, HTTPS (or, for tests, file) URLs, well-formed hashes and sizes.
    public static func decode(_ data: Data) throws -> ModelManifest {
        let manifest = try JSONDecoder().decode(ModelManifest.self, from: data)
        try manifest.validate()
        return manifest
    }
    public func validate() throws {
        func fail(_ text: String) -> ParzrError { .message("The model manifest is invalid: \(text)") }
        guard schema == 1 else { throw fail("schema \(schema)") }
        for pack in packs {
            for part in [pack.id, pack.version] where part.isEmpty || part.hasPrefix(".") || part.contains("/") { throw fail("pack \(part)") }
            for file in pack.files {
                let parts = file.path.split(separator: "/", omittingEmptySubsequences: false)
                guard !file.path.hasPrefix("/"), parts.allSatisfy({ !$0.isEmpty && !$0.hasPrefix(".") }) else { throw fail("path \(file.path)") }
                guard let url = URL(string: file.url), url.scheme == "https" || url.scheme == "file" else { throw fail("URL \(file.url)") }
                guard file.sha256.count == 64, file.sha256.allSatisfy({ $0.isHexDigit && !$0.isUppercase }), file.bytes > 0 else { throw fail("hash or size of \(file.path)") }
            }
        }
    }
    /// The pack that holds the models for typing and Option+Space (the one that provides the writing model).
    public var essential: ModelPack? { packs.first { $0.provides["writing_model"] != nil } ?? packs.first }
}

/// Why a pack is not ready. Every case leaves Parzr working with its rules.
public enum ModelPackFailure: Equatable, Sendable {
    case offline
    /// The pack's release is not on GitHub (yet): 404 or 410.
    case unavailable(status: Int)
    case server(status: Int)
    /// A file did not match its SHA-256 twice in a row.
    case corrupt(String)
    case diskFull(needed: Int64)
    case other(String)
    public var message: String {
        switch self {
        case .offline: "No internet connection. Parzr tries again when you are back online."
        case .unavailable: "The models are not available for download yet. Parzr tries again later."
        case .server(let status): "GitHub did not answer (error \(status)). Parzr tries again shortly."
        case .corrupt: "A download was damaged, so Parzr did not use it. Try again."
        case .diskFull(let needed): "Not enough free space. Smart grammar needs \(ByteCountFormatter.string(fromByteCount: needed, countStyle: .file)) free."
        case .other(let text): text
        }
    }
    /// Retried on its own (back online, a later attempt); a full disk and a damaged download wait for the user.
    public var retriesAutomatically: Bool { switch self { case .offline, .unavailable, .server, .other: true; case .corrupt, .diskFull: false } }
}

public enum ModelPackState: Equatable, Sendable {
    /// Not on this Mac and not downloading (never started, removed, or waiting for the welcome guide).
    case missing
    case downloading(received: Int64, total: Int64)
    case verifying
    case ready
    case failed(ModelPackFailure)
    /// Development: PARZR_MODEL_PATH or PARZR_GEC_DIR point the engine at other files, so nothing is downloaded.
    case development
    public var isReady: Bool { self == .ready || self == .development }
    public var isWorking: Bool { switch self { case .downloading, .verifying: true; default: false } }
    public var fraction: Double? {
        switch self {
        case .downloading(let received, let total) where total > 0: min(1, Double(received) / Double(total))
        case .verifying: 1
        default: nil
        }
    }
}

/// Where downloaded bytes go: a partial file, appended to. The transport writes from its own queue, so a full disk stops the download at once.
public final class ModelSink: @unchecked Sendable {
    private let handle: FileHandle
    private let lock = NSLock()
    private var written: Int64
    private let progress: @Sendable (Int64) -> Void
    init(handle: FileHandle, offset: Int64, progress: @escaping @Sendable (Int64) -> Void) { self.handle = handle; written = offset; self.progress = progress }
    /// The server sent the whole file, not the requested range: start the partial file over.
    public func restart() throws {
        try lock.withLock { try handle.truncate(atOffset: 0); try handle.seek(toOffset: 0); written = 0 }
        progress(0)
    }
    public func write(_ data: Data) throws {
        let total: Int64 = try lock.withLock { try handle.write(contentsOf: data); written += Int64(data.count); return written }
        progress(total)
    }
    var count: Int64 { lock.withLock { written } }
}

/// Fetches a URL from a byte offset into a sink. URLSessionTransport in the app; tests use a fake.
public protocol ModelTransport: Sendable {
    func download(_ url: URL, from offset: Int64, into sink: ModelSink) async throws
}

/// A transport error with what it means for the pack.
public struct ModelTransportError: Error, Equatable {
    public var failure: ModelPackFailure
    /// The server cannot serve the requested range (416): the partial file is stale.
    public var rangeRejected = false
    public init(_ failure: ModelPackFailure, rangeRejected: Bool = false) { self.failure = failure; self.rangeRejected = rangeRejected }
}

/// The on-disk side of model packs: install (download, verify, move into place), check, remove.
public struct ModelStore: Sendable {
    public let root: URL
    public let transport: any ModelTransport
    /// Replaces the release download URL's folder (development and tests: a local copy of the pack). Hashes are still checked.
    public var baseURL: URL?
    /// Free bytes on the models volume; nil when unknown (the download is then attempted, and a full disk still fails cleanly).
    public var freeSpace: @Sendable (URL) -> Int64? = ModelStore.availableCapacity
    public init(root: URL, transport: any ModelTransport, baseURL: URL? = nil) { self.root = root; self.transport = transport; self.baseURL = baseURL }

    /// PARZR_MODELS_DIR, else ~/Library/Application Support/Parzr/Models (the engine reads the same place).
    public static func defaultRoot(environment: [String: String] = ProcessInfo.processInfo.environment) -> URL {
        if let custom = environment["PARZR_MODELS_DIR"], !custom.isEmpty { return URL(fileURLWithPath: custom, isDirectory: true) }
        let support = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask).first ?? URL(fileURLWithPath: NSHomeDirectory()).appendingPathComponent("Library/Application Support")
        return support.appendingPathComponent("Parzr/Models", isDirectory: true)
    }
    public static func availableCapacity(_ url: URL) -> Int64? {
        var probe = url
        while !FileManager.default.fileExists(atPath: probe.path), probe.pathComponents.count > 1 { probe.deleteLastPathComponent() }
        return (try? probe.resourceValues(forKeys: [.volumeAvailableCapacityForImportantUsageKey]))?.volumeAvailableCapacityForImportantUsage
    }

    public func folder(_ pack: ModelPack) -> URL { root.appendingPathComponent(pack.id, isDirectory: true).appendingPathComponent(pack.version, isDirectory: true) }
    func staging(_ pack: ModelPack) -> URL { root.appendingPathComponent(pack.id, isDirectory: true).appendingPathComponent(".download-\(pack.version)", isDirectory: true) }
    func url(for file: ModelFile) -> URL? {
        guard let original = URL(string: file.url) else { return nil }
        return baseURL.map { $0.appendingPathComponent(original.lastPathComponent) } ?? original
    }

    /// The verified version folder is in place with every file at its pinned size (hashes were checked when it was installed).
    public func isInstalled(_ pack: ModelPack) -> Bool {
        let folder = folder(pack)
        return pack.files.allSatisfy { file in
            let attributes = try? FileManager.default.attributesOfItem(atPath: folder.appendingPathComponent(file.path).path)
            return (attributes?[.size] as? NSNumber)?.int64Value == file.bytes
        }
    }
    /// Bytes already downloaded towards `pack`: its verified files and partial files in the staging folder.
    public func downloaded(_ pack: ModelPack) -> Int64 {
        let staging = staging(pack)
        return pack.files.reduce(0) { sum, file in
            let done = staging.appendingPathComponent(file.path), partial = staging.appendingPathComponent(file.path + ".partial")
            if let size = Self.size(done), size == file.bytes { return sum + size }
            return sum + min(file.bytes, Self.size(partial) ?? 0)
        }
    }

    /// Downloads what is missing, verifies every file, and moves the pack into place; older versions are removed afterwards.
    /// Reports progress through `update` and returns `.ready` or `.failed`. Cancelling the task stops it and keeps the partial files for a resume.
    public func install(_ pack: ModelPack, update: @escaping @Sendable (ModelPackState) -> Void = { _ in }) async -> ModelPackState {
        if isInstalled(pack) { removeOthers(pack); return .ready }
        let staging = staging(pack), files = FileManager.default, total = pack.bytes
        do {
            try files.createDirectory(at: staging, withIntermediateDirectories: true)
            let needed = total - downloaded(pack)
            if let free = freeSpace(root), free < needed + 50_000_000 { return .failed(.diskFull(needed: needed + 50_000_000)) }
            var finished: Int64 = 0
            for file in pack.files {
                try Task.checkCancellation()
                let target = staging.appendingPathComponent(file.path)
                if Self.size(target) == file.bytes, try Self.sha256(of: target) == file.sha256 { finished += file.bytes; continue }
                try? files.removeItem(at: target)
                try files.createDirectory(at: target.deletingLastPathComponent(), withIntermediateDirectories: true)
                let base = finished
                update(.downloading(received: base, total: total))
                try await fetch(file, to: target) { update(.downloading(received: base + $0, total: total)) }
                finished += file.bytes
            }
            try Task.checkCancellation()
            update(.verifying)
            let data = try JSONEncoder().encode(pack)
            try data.write(to: staging.appendingPathComponent("pack.json"), options: .atomic)
            let folder = folder(pack)
            if files.fileExists(atPath: folder.path) { try discard(folder) }
            try files.moveItem(at: staging, to: folder)
            removeOthers(pack)
            return .ready
        } catch let error as ModelTransportError { return .failed(error.failure) }
        catch is CancellationError { return .missing }
        catch { return .failed(Self.failure(for: error, needed: total)) }
    }

    /// One file: resume its partial file, verify size and SHA-256, rename into place. A damaged file is fetched once more from the start.
    private func fetch(_ file: ModelFile, to target: URL, progress: @escaping @Sendable (Int64) -> Void) async throws {
        guard let url = url(for: file) else { throw ModelTransportError(.other("The model address is invalid.")) }
        let partial = target.deletingLastPathComponent().appendingPathComponent(target.lastPathComponent + ".partial")
        for attempt in 0..<2 {
            var offset = Self.size(partial) ?? 0
            if offset > file.bytes || attempt > 0 { try? FileManager.default.removeItem(at: partial); offset = 0 }
            if !FileManager.default.fileExists(atPath: partial.path) { FileManager.default.createFile(atPath: partial.path, contents: nil) }
            let handle = try FileHandle(forWritingTo: partial)
            let sink: ModelSink
            do { try handle.seek(toOffset: UInt64(offset)); sink = ModelSink(handle: handle, offset: offset, progress: progress) } catch { try? handle.close(); throw error }
            if offset < file.bytes {
                do { try await transport.download(url, from: offset, into: sink) }
                catch let error as ModelTransportError where error.rangeRejected {
                    try? handle.close(); try? FileManager.default.removeItem(at: partial); continue
                } catch { try? handle.close(); throw error }
            }
            try handle.close()
            guard sink.count == file.bytes, try Self.sha256(of: partial) == file.sha256 else {
                if attempt == 0 { continue }
                try? FileManager.default.removeItem(at: partial)
                throw ModelTransportError(.corrupt(file.path))
            }
            try FileManager.default.moveItem(at: partial, to: target)
            return
        }
        throw ModelTransportError(.corrupt(file.path))
    }

    /// Removes the pack (its verified folder and any partial download). The folder is renamed first, so the engine never sees half of it.
    public func remove(_ pack: ModelPack) throws {
        for folder in [folder(pack), staging(pack)] where FileManager.default.fileExists(atPath: folder.path) { try discard(folder) }
    }
    /// Everything in the pack's folder except this version and its download: older versions, abandoned downloads.
    func removeOthers(_ pack: ModelPack) {
        let parent = root.appendingPathComponent(pack.id, isDirectory: true)
        let keep: Set<String> = [pack.version, ".download-\(pack.version)"]
        for entry in (try? FileManager.default.contentsOfDirectory(atPath: parent.path)) ?? [] where !keep.contains(entry) {
            try? discard(parent.appendingPathComponent(entry))
        }
    }
    private func discard(_ url: URL) throws {
        let trash = url.deletingLastPathComponent().appendingPathComponent(".trash-\(UUID().uuidString)")
        try FileManager.default.moveItem(at: url, to: trash)
        try FileManager.default.removeItem(at: trash)
    }

    static func size(_ url: URL) -> Int64? { ((try? FileManager.default.attributesOfItem(atPath: url.path))?[.size] as? NSNumber)?.int64Value }
    public static func sha256(of url: URL) throws -> String {
        let handle = try FileHandle(forReadingFrom: url)
        defer { try? handle.close() }
        var hasher = SHA256()
        while let chunk = try handle.read(upToCount: 4 << 20), !chunk.isEmpty { hasher.update(data: chunk) }
        return hasher.finalize().map { String(format: "%02x", $0) }.joined()
    }
    /// A full disk, a missing connection, or anything else, in the user's terms.
    public static func failure(for error: Error, needed: Int64) -> ModelPackFailure {
        if let error = error as? ModelTransportError { return error.failure }
        let ns = error as NSError
        if ns.domain == NSCocoaErrorDomain && ns.code == NSFileWriteOutOfSpaceError { return .diskFull(needed: needed) }
        if ns.domain == NSPOSIXErrorDomain && (ns.code == Int(ENOSPC) || ns.code == Int(EDQUOT)) { return .diskFull(needed: needed) }
        if let posix = ns.userInfo[NSUnderlyingErrorKey] as? NSError, posix.domain == NSPOSIXErrorDomain, posix.code == Int(ENOSPC) { return .diskFull(needed: needed) }
        if ns.domain == NSURLErrorDomain, offlineCodes.contains(ns.code) { return .offline }
        return .other("The download stopped: \(ns.localizedDescription)")
    }
    static let offlineCodes: Set<Int> = [NSURLErrorNotConnectedToInternet, NSURLErrorNetworkConnectionLost, NSURLErrorTimedOut, NSURLErrorCannotFindHost, NSURLErrorCannotConnectToHost, NSURLErrorDNSLookupFailed, NSURLErrorInternationalRoamingOff, NSURLErrorDataNotAllowed, NSURLErrorCallIsActive]
}

/// Plain HTTPS GETs of the pinned release files: an ephemeral session (no cookies, no cache, no credentials), a fixed
/// user agent, and a Range header to resume. Nothing about the user or their writing is sent. Also reads file:// copies.
public final class URLSessionTransport: NSObject, ModelTransport, URLSessionDataDelegate, @unchecked Sendable {
    private final class Job {
        let sink: ModelSink
        let offset: Int64
        let continuation: CheckedContinuation<Void, Error>
        var failure: Error?
        init(sink: ModelSink, offset: Int64, continuation: CheckedContinuation<Void, Error>) { self.sink = sink; self.offset = offset; self.continuation = continuation }
    }
    private let lock = NSLock()
    private var jobs: [Int: Job] = [:]
    private var session: URLSession!
    public override init() {
        super.init()
        let configuration = URLSessionConfiguration.ephemeral
        configuration.httpCookieStorage = nil; configuration.httpShouldSetCookies = false; configuration.urlCache = nil; configuration.urlCredentialStorage = nil
        configuration.requestCachePolicy = .reloadIgnoringLocalCacheData
        configuration.httpAdditionalHeaders = ["User-Agent": "Parzr"]
        configuration.timeoutIntervalForRequest = 60
        configuration.waitsForConnectivity = false
        let queue = OperationQueue(); queue.maxConcurrentOperationCount = 1; queue.name = "Parzr model download"
        session = URLSession(configuration: configuration, delegate: self, delegateQueue: queue)
    }

    public func download(_ url: URL, from offset: Int64, into sink: ModelSink) async throws {
        var request = URLRequest(url: url)
        if offset > 0 { request.setValue("bytes=\(offset)-", forHTTPHeaderField: "Range") }
        let task = session.dataTask(with: request)
        try await withTaskCancellationHandler {
            try await withCheckedThrowingContinuation { (continuation: CheckedContinuation<Void, Error>) in
                lock.withLock { jobs[task.taskIdentifier] = Job(sink: sink, offset: offset, continuation: continuation) }
                task.resume()
            }
        } onCancel: { task.cancel() }
    }
    private func job(_ task: URLSessionTask) -> Job? { lock.withLock { jobs[task.taskIdentifier] } }

    public func urlSession(_ session: URLSession, dataTask: URLSessionDataTask, didReceive response: URLResponse, completionHandler: @escaping (URLSession.ResponseDisposition) -> Void) {
        guard let job = job(dataTask) else { completionHandler(.cancel); return }
        do {
            if let http = response as? HTTPURLResponse {
                switch http.statusCode {
                case 206: break
                case 200: if job.offset > 0 { try job.sink.restart() }   // the server ignored the range: the whole file follows
                case 416: throw ModelTransportError(.server(status: 416), rangeRejected: true)
                case 404, 410: throw ModelTransportError(.unavailable(status: http.statusCode))
                default: throw ModelTransportError(.server(status: http.statusCode))
                }
            } else if job.offset > 0 { try job.sink.restart() }   // file:// has no ranges
            completionHandler(.allow)
        } catch { job.failure = error; completionHandler(.cancel) }
    }
    public func urlSession(_ session: URLSession, dataTask: URLSessionDataTask, didReceive data: Data) {
        guard let job = job(dataTask), job.failure == nil else { return }
        do { try job.sink.write(data) } catch { job.failure = error; dataTask.cancel() }
    }
    public func urlSession(_ session: URLSession, task: URLSessionTask, didCompleteWithError error: Error?) {
        guard let job = lock.withLock({ jobs.removeValue(forKey: task.taskIdentifier) }) else { return }
        if let failure = job.failure { job.continuation.resume(throwing: failure) }
        else if let error { job.continuation.resume(throwing: (error as NSError).code == NSURLErrorCancelled ? CancellationError() : error) }
        else { job.continuation.resume() }
    }
}
