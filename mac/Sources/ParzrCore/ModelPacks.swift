import CryptoKit
import Darwin
import Foundation

// Model packs: the model files Parzr downloads on demand instead of shipping them in the app.
// The pinned manifest is compiled into the engine (engine/models.json) and read through `parzr_model_manifest`.
// A pack is staged in `<root>/<pack>/.download-<version>/` (each file as `<name>.partial`, resumed with a Range
// request, then checked against its SHA-256 and renamed), and the folder is renamed to `<root>/<pack>/<version>/`
// only when every file is verified. The folder alone is never trusted: once every file matched its SHA-256 the app writes
// `.verified.json` beside them (each file's pinned hash and its size, inode and modification time), and the engine uses a
// pack only while every file still matches it (engine/src/packs.rs). Each run re-hashes the installed packs once, in the
// background, before anything loads them (the engine is held meanwhile); a pack that no longer matches is set aside.

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
    /// The pack that provides `role` (an optional pack's role, such as "slip_model" or "tone_model"), if this manifest has one.
    public func pack(providing role: String) -> ModelPack? { packs.first { $0.provides[role] != nil } }
    /// The optional pack of the typing-time slip check.
    public var slips: ModelPack? { pack(providing: OptionalPack.slips.role) }
    /// The optional pack of the tone check.
    public var tone: ModelPack? { pack(providing: OptionalPack.tone.role) }
}

/// A pack beyond the essential one: a feature of its own, with its own download, Remove and Settings section. Every
/// optional pack is described here and driven by the same `ModelCenter`; adding one is a value below plus its catalog entry.
public struct OptionalPack: Sendable, Equatable, Identifiable {
    /// What the pack provides in engine/models.json ("slip_model", "tone_model").
    public let role: String
    /// The feature in the surfaces' words ("Slip check", "Tone check").
    public let feature: String
    /// Development: this variable points at local files instead, so nothing is downloaded.
    public let developmentVariable: String
    /// Downloads on its own once the essential pack is ready, while its check is switched on (true), or only when the
    /// user asks for it in Settings, Models (false).
    public let automatic: Bool
    /// What Parzr does without it, while it is missing and after the user removed it.
    public let missingNote: String
    public let removedNote: String
    public var id: String { role }
    public init(role: String, feature: String, developmentVariable: String, automatic: Bool, missingNote: String, removedNote: String) {
        self.role = role; self.feature = feature; self.developmentVariable = developmentVariable; self.automatic = automatic; self.missingNote = missingNote; self.removedNote = removedNote
    }
    public static let slips = OptionalPack(role: "slip_model", feature: "Slip check", developmentVariable: "PARZR_SLIP_DIR", automatic: true,
                                           missingNote: "Word-choice slips are checked on Option+Space until it arrives.",
                                           removedNote: "Word-choice slips are checked only on Option+Space until you download it.")
    public static let tone = OptionalPack(role: "tone_model", feature: "Tone check", developmentVariable: "PARZR_TONE_DIR", automatic: true,
                                          missingNote: "Tone check flags nothing until it arrives.",
                                          removedNote: "Tone check flags nothing until you download it again.")
    /// Settings, Models, while the check is switched off in Settings, Writing: nothing downloads on its own.
    public var switchedOffNote: String { "\(feature) is off in Settings, Writing, so it is not downloaded on its own." }
    /// Every optional pack, in the order Settings lists them.
    public static let all: [OptionalPack] = [.slips, .tone]
}

/// Why a pack is not ready. Every case leaves Parzr working with its rules.
public enum ModelPackFailure: Equatable, Sendable {
    case offline
    /// The pack's release is not on GitHub (yet): 404 or 410.
    case unavailable(status: Int)
    case server(status: Int)
    /// A file did not match its SHA-256 twice in a row.
    case corrupt(String)
    /// An installed file no longer matches its SHA-256 (checked again each run): the pack was set aside.
    case changedOnDisk(String)
    case diskFull(needed: Int64)
    case other(String)
    public var message: String {
        switch self {
        case .offline: "No internet connection. Parzr tries again when you are back online."
        case .unavailable: "The models are not available for download yet. Parzr tries again later."
        case .server(let status): "GitHub did not answer (error \(status)). Parzr tries again shortly."
        case .corrupt: "A download was damaged, so Parzr did not use it. Try again."
        case .changedOnDisk: "The downloaded models no longer match their checksums, so Parzr set them aside and checks with its rules. Download them again."
        case .diskFull(let needed): "Not enough free space. Smart grammar needs \(ByteCountFormatter.string(fromByteCount: needed, countStyle: .file)) free."
        case .other(let text): text
        }
    }
    /// Retried on its own (back online, a later attempt); a full disk and a damaged download wait for the user.
    public var retriesAutomatically: Bool { switch self { case .offline, .unavailable, .server, .other: true; case .corrupt, .changedOnDisk, .diskFull: false } }
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

/// A server sent more bytes than the file's pinned size: the download is refused (and fetched once more from the start).
public struct ModelOverflow: Error, Equatable {}

/// Where downloaded bytes go: a partial file, appended to. The transport writes from its own queue, so a full disk stops the download at once.
/// Nothing past the file's pinned size is ever written (`limit`).
public final class ModelSink: @unchecked Sendable {
    private let handle: FileHandle
    private let lock = NSLock()
    private var written: Int64
    private let progress: @Sendable (Int64) -> Void
    /// The file's pinned size: the most the partial file may hold.
    public let limit: Int64
    /// The offset the transport asked for (a resume), which a 206 answer's Content-Range must start at.
    public let offset: Int64
    init(handle: FileHandle, offset: Int64, limit: Int64, progress: @escaping @Sendable (Int64) -> Void) { self.handle = handle; written = offset; self.offset = offset; self.limit = limit; self.progress = progress }
    /// The server sent the whole file, not the requested range: start the partial file over.
    public func restart() throws {
        try lock.withLock { try handle.truncate(atOffset: 0); try handle.seek(toOffset: 0); written = 0 }
        progress(0)
    }
    public func write(_ data: Data) throws {
        let total: Int64 = try lock.withLock {
            guard written + Int64(data.count) <= limit else { throw ModelOverflow() }
            try handle.write(contentsOf: data); written += Int64(data.count); return written
        }
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
/// A regular file's identity on disk: its size, inode and modification time (nanoseconds), and its volume. A verdict about
/// its contents holds while this is unchanged; the engine compares the same size, inode and time with `.verified.json`.
public struct FileIdentity: Equatable, Hashable, Sendable {
    public var bytes: Int64
    public var inode: UInt64
    public var mtimeNs: Int64
    public var device: Int64
    /// Nil for anything but a regular file (a symbolic link, a folder, a missing file).
    public static func of(_ url: URL) -> FileIdentity? {
        var info = stat()
        guard lstat(url.path, &info) == 0, (info.st_mode & S_IFMT) == S_IFREG else { return nil }
        let (seconds, overflow) = Int64(info.st_mtimespec.tv_sec).multipliedReportingOverflow(by: 1_000_000_000)
        guard !overflow else { return nil }
        return FileIdentity(bytes: Int64(info.st_size), inode: UInt64(info.st_ino), mtimeNs: seconds + Int64(info.st_mtimespec.tv_nsec), device: Int64(info.st_dev))
    }
}

/// This run's verdicts: the SHA-256 a file had, by its identity. A file is hashed again only when its identity changes (or in the next run).
public final class VerifiedFiles: @unchecked Sendable {
    public static let shared = VerifiedFiles()
    private let lock = NSLock()
    private var hashes: [FileIdentity: String] = [:]
    public init() {}
    func sha256(_ identity: FileIdentity) -> String? { lock.withLock { hashes[identity] } }
    func record(_ identity: FileIdentity, sha256: String) { lock.withLock { hashes[identity] = sha256 } }
}

/// What `.verified.json` holds (engine/src/packs.rs reads it).
struct VerifiedMarker: Codable, Equatable {
    struct Entry: Codable, Equatable {
        var path: String, sha256: String, bytes: Int64, inode: UInt64, mtimeNs: Int64
        enum CodingKeys: String, CodingKey { case path, sha256, bytes, inode, mtimeNs = "mtime_ns" }
    }
    var schema = 1
    var pack: String, version: String
    var files: [Entry]
}

public struct ModelStore: Sendable {
    public let root: URL
    public let transport: any ModelTransport
    /// This run's hash verdicts (tests pass a fresh one to stand for the next launch).
    public var verified: VerifiedFiles = .shared
    /// The marker beside a verified pack's files.
    public static let marker = ".verified.json"
    /// Replaces the release download URL's folder (development and tests: a local copy of the pack). Hashes are still checked.
    public var baseURL: URL?
    /// Free bytes on the models volume; nil when unknown (the download is then attempted, and a full disk still fails cleanly).
    public var freeSpace: @Sendable (URL) -> Int64? = ModelStore.availableCapacity
    public init(root: URL, transport: any ModelTransport, baseURL: URL? = nil) { self.root = root; self.transport = transport; self.baseURL = baseURL }

    /// PARZR_MODELS_DIR (a development override, see `DevOverrides`), else ~/Library/Application Support/Parzr/Models (the engine reads the same place).
    public static func defaultRoot(environment: [String: String] = ProcessInfo.processInfo.environment) -> URL {
        if let custom = DevOverrides.value("PARZR_MODELS_DIR", in: environment) { return URL(fileURLWithPath: custom, isDirectory: true) }
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

    /// The version folder is in place with every file at its pinned size. Cheap; whether the files are the verified ones is
    /// `verifiedThisRun` (no hashing) and `verify` (hashes what this run has not).
    public func isInstalled(_ pack: ModelPack) -> Bool {
        let folder = folder(pack)
        return pack.files.allSatisfy { file in
            let attributes = try? FileManager.default.attributesOfItem(atPath: folder.appendingPathComponent(file.path).path)
            return (attributes?[.size] as? NSNumber)?.int64Value == file.bytes
        }
    }
    /// This run hashed every file of the installed pack and none has changed since: it may be used without reading it again.
    public func verifiedThisRun(_ pack: ModelPack) -> Bool {
        let folder = folder(pack)
        return pack.files.allSatisfy { file in
            guard let identity = FileIdentity.of(folder.appendingPathComponent(file.path)), identity.bytes == file.bytes else { return false }
            return verified.sha256(identity) == file.sha256
        }
    }
    public enum Verification: Equatable, Sendable { case verified, mismatch(String) }
    /// Checks every file of the installed pack against its pinned SHA-256: a file this run already hashed, and that has not
    /// changed since (same identity), is not read again. On success writes the marker the engine requires, naming each
    /// file as it was hashed. A missing file, a symbolic link or any other hash is a mismatch.
    public func verify(_ pack: ModelPack) throws -> Verification {
        let folder = folder(pack)
        var entries: [VerifiedMarker.Entry] = []
        for file in pack.files {
            try Task.checkCancellation()
            let url = folder.appendingPathComponent(file.path)
            guard let before = FileIdentity.of(url), before.bytes == file.bytes else { return .mismatch(file.path) }
            if verified.sha256(before) != file.sha256 {
                guard let sha = try? Self.sha256(of: url), FileIdentity.of(url) == before else { return .mismatch(file.path) }
                guard sha == file.sha256 else { return .mismatch(file.path) }
                verified.record(before, sha256: sha)
            }
            entries.append(.init(path: file.path, sha256: file.sha256, bytes: before.bytes, inode: before.inode, mtimeNs: before.mtimeNs))
        }
        let marker = VerifiedMarker(pack: pack.id, version: pack.version, files: entries)
        let encoder = JSONEncoder(); encoder.outputFormatting = [.sortedKeys]
        try encoder.encode(marker).write(to: folder.appendingPathComponent(Self.marker), options: .atomic)
        return .verified
    }
    /// Sets an installed pack that failed its check aside (renamed out of the version folder, so the engine never reads it;
    /// the next install removes it). Its marker goes with it.
    public func quarantine(_ pack: ModelPack) throws {
        let folder = folder(pack)
        guard FileManager.default.fileExists(atPath: folder.path) else { return }
        let aside = root.appendingPathComponent(pack.id, isDirectory: true).appendingPathComponent(".quarantine-\(pack.version)-\(UUID().uuidString)", isDirectory: true)
        try FileManager.default.moveItem(at: folder, to: aside)
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
        if isInstalled(pack) {
            // Already here: used only once its files check out; otherwise set aside and downloaded again.
            if (try? verify(pack)) == .verified { removeOthers(pack); return .ready }
            try? quarantine(pack)
        }
        let staging = staging(pack), files = FileManager.default, total = pack.bytes
        do {
            try files.createDirectory(at: staging, withIntermediateDirectories: true)
            let needed = total - downloaded(pack)
            if let free = freeSpace(root), free < needed + 50_000_000 { return .failed(.diskFull(needed: needed + 50_000_000)) }
            var finished: Int64 = 0
            for file in pack.files {
                try Task.checkCancellation()
                let target = staging.appendingPathComponent(file.path)
                if let identity = FileIdentity.of(target), identity.bytes == file.bytes, try Self.sha256(of: target) == file.sha256, FileIdentity.of(target) == identity {
                    verified.record(identity, sha256: file.sha256); finished += file.bytes; continue
                }
                try? files.removeItem(at: target)
                try files.createDirectory(at: target.deletingLastPathComponent(), withIntermediateDirectories: true)
                let base = finished, resumed = min(file.bytes, Self.size(staging.appendingPathComponent(file.path + ".partial")) ?? 0)
                update(.downloading(received: base + resumed, total: total))
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
            // Every file was hashed on the way in (and a rename keeps its identity), so this writes the marker without reading them again.
            guard try verify(pack) == .verified else { try? quarantine(pack); return .failed(.corrupt(pack.files.first?.path ?? pack.id)) }
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
            do { try handle.seek(toOffset: UInt64(offset)); sink = ModelSink(handle: handle, offset: offset, limit: file.bytes, progress: progress) } catch { try? handle.close(); throw error }
            if offset < file.bytes {
                do { try await transport.download(url, from: offset, into: sink) }
                catch let error as ModelTransportError where error.rangeRejected {
                    try? handle.close(); try? FileManager.default.removeItem(at: partial); continue
                } catch is ModelOverflow {
                    // More than the pinned size: never kept, fetched once more from the start, then refused.
                    try? handle.close(); try? FileManager.default.removeItem(at: partial)
                    if attempt == 0 { continue }
                    throw ModelTransportError(.corrupt(file.path))
                } catch { try? handle.close(); throw error }
            }
            try handle.close()
            let identity = FileIdentity.of(partial)
            guard sink.count == file.bytes, identity?.bytes == file.bytes, try Self.sha256(of: partial) == file.sha256, FileIdentity.of(partial) == identity, let identity else {
                if attempt == 0 { continue }
                try? FileManager.default.removeItem(at: partial)
                throw ModelTransportError(.corrupt(file.path))
            }
            try FileManager.default.moveItem(at: partial, to: target)
            verified.record(identity, sha256: file.sha256)
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

    /// A 206 answer's `Content-Range: bytes START-END/TOTAL` fits a resume from `offset` of a `total`-byte file: it starts
    /// at the offset and runs to the file's last byte, and the total (unless the server says `*`) is the pinned size.
    public static func contentRangeMatches(_ header: String?, offset: Int64, total: Int64) -> Bool {
        guard let header else { return false }
        let parts = header.trimmingCharacters(in: .whitespaces).split(separator: " ", maxSplits: 1)
        guard parts.count == 2, parts[0].lowercased() == "bytes" else { return false }
        let range = parts[1].split(separator: "/", maxSplits: 1)
        guard range.count == 2 else { return false }
        let bounds = range[0].split(separator: "-", maxSplits: 1)
        guard bounds.count == 2, let start = Int64(bounds[0]), let end = Int64(bounds[1]), start == offset, end >= start, end == total - 1 else { return false }
        return range[1] == "*" || Int64(range[1]) == total
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
                case 206:
                    // A resumed answer must start where the partial file ends and describe the pinned file; anything else starts over.
                    guard ModelStore.contentRangeMatches(http.value(forHTTPHeaderField: "Content-Range"), offset: job.offset, total: job.sink.limit) else {
                        throw ModelTransportError(.server(status: 206), rangeRejected: true)
                    }
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
