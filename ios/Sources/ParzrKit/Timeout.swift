import Foundation

public struct TimedOut: Error, Equatable {}

/// Runs `operation`, giving up after `timeout`. Unlike a task group this returns at the
/// deadline even when the operation ignores cancellation (an Apple Intelligence call can stall
/// for over a minute; Parzr waits about 3 s).
public func withTimeout<T: Sendable>(_ timeout: Duration, operation: @escaping @Sendable () async throws -> T) async throws -> T {
    let once = Once<T>()
    return try await withTaskCancellationHandler {
        try await withCheckedThrowingContinuation { continuation in
            once.set(continuation)
            let work = Task {
                do { once.resume(.success(try await operation())) } catch { once.resume(.failure(error)) }
            }
            once.onFinish { work.cancel() }
            Task {
                try? await Task.sleep(for: timeout)
                once.resume(.failure(TimedOut()))
            }
        }
    } onCancel: {
        once.resume(.failure(CancellationError()))
    }
}

/// Resumes a continuation exactly once, from whichever side finishes first.
private final class Once<T: Sendable>: @unchecked Sendable {
    private let lock = NSLock()
    private var continuation: CheckedContinuation<T, Error>?
    private var early: Result<T, Error>?
    private var done = false
    private var finish: (@Sendable () -> Void)?

    func set(_ continuation: CheckedContinuation<T, Error>) {
        lock.lock()
        if let early { lock.unlock(); continuation.resume(with: early); return }
        self.continuation = continuation
        lock.unlock()
    }
    func onFinish(_ action: @escaping @Sendable () -> Void) {
        lock.lock()
        if done { lock.unlock(); action(); return }
        finish = action
        lock.unlock()
    }
    func resume(_ result: Result<T, Error>) {
        lock.lock()
        guard !done else { lock.unlock(); return }
        done = true
        let continuation = self.continuation, finish = self.finish
        self.continuation = nil; self.finish = nil
        if continuation == nil { early = result }
        lock.unlock()
        continuation?.resume(with: result)
        finish?()
    }
}
