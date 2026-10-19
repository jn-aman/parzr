import UIKit

/// A plain QWERTY layout with a numbers-and-symbols layer. Kept in UIKit and small: a keyboard
/// extension shares a tight memory limit with everything else it loads.
final class KeysView: UIView {
    enum Page { case letters, numbers, symbols }
    enum Shift { case off, once, locked }

    var onText: ((String) -> Void)?
    var onDelete: (() -> Void)?
    var onReturn: (() -> Void)?
    /// The globe key: the controller wires it to `handleInputModeList(from:with:)`.
    let globe = KeysView.key("globe", symbol: true)
    var showsGlobe = true { didSet { if oldValue != showsGlobe { rebuild() } } }

    private(set) var page: Page = .letters
    var shift: Shift = .once { didSet { if oldValue != shift { rebuild() } } }
    private let rows = UIStackView()
    private var deleteTimer: Timer?

    private static let letters = ["qwertyuiop", "asdfghjkl", "zxcvbnm"]
    private static let numbers = ["1234567890", "-/:;()$&@\"", ".,?!'"]
    private static let symbols = ["[]{}#%^*+=", "_\\|~<>€£¥•", ".,?!'"]

    override init(frame: CGRect) {
        super.init(frame: frame)
        rows.axis = .vertical
        rows.spacing = 8
        rows.distribution = .fillEqually
        rows.translatesAutoresizingMaskIntoConstraints = false
        addSubview(rows)
        NSLayoutConstraint.activate([
            rows.leadingAnchor.constraint(equalTo: leadingAnchor, constant: 3),
            rows.trailingAnchor.constraint(equalTo: trailingAnchor, constant: -3),
            rows.topAnchor.constraint(equalTo: topAnchor, constant: 6),
            rows.bottomAnchor.constraint(equalTo: bottomAnchor, constant: -4),
        ])
        globe.accessibilityLabel = "Next keyboard"
        globe.widthAnchor.constraint(equalToConstant: 44).isActive = true
        rebuild()
    }
    required init?(coder: NSCoder) { fatalError("init(coder:) is not used") }

    private func rebuild() {
        rows.arrangedSubviews.forEach { $0.removeFromSuperview() }
        let source = page == .letters ? Self.letters : page == .numbers ? Self.numbers : Self.symbols
        for (index, line) in source.enumerated() {
            let row = UIStackView()
            row.spacing = 6
            row.distribution = .fill
            var keys: [UIButton] = line.map { character in
                let text = page == .letters && shift != .off ? String(character).uppercased() : String(character)
                let button = Self.key(text)
                button.addAction(UIAction { [weak self] _ in self?.typed(text) }, for: .touchUpInside)
                return button
            }
            let wide = index == source.count - 1
            if wide {
                let left: UIButton
                if page == .letters {
                    left = Self.key(shift == .locked ? "capslock.fill" : shift == .once ? "shift.fill" : "shift", symbol: true)
                    left.accessibilityLabel = "Shift"
                    left.addAction(UIAction { [weak self] _ in self?.toggleShift() }, for: .touchUpInside)
                } else {
                    left = Self.key(page == .numbers ? "#+=" : "123", dark: true)
                    left.addAction(UIAction { [weak self] _ in self?.switchTo(self?.page == .numbers ? .symbols : .numbers) }, for: .touchUpInside)
                }
                let delete = Self.key("delete.left", symbol: true)
                delete.accessibilityLabel = "Delete"
                delete.addAction(UIAction { [weak self] _ in self?.startDeleting() }, for: .touchDown)
                delete.addAction(UIAction { [weak self] _ in self?.stopDeleting() }, for: [.touchUpInside, .touchUpOutside, .touchCancel])
                keys.insert(left, at: 0)
                keys.append(delete)
            }
            keys.forEach(row.addArrangedSubview)
            if wide, let first = keys.first, let last = keys.last, keys.count > 2 {
                // Shift and delete are wider; the letters share the rest equally.
                let letter = keys[1]
                for key in keys.dropFirst().dropLast() where key !== letter { key.widthAnchor.constraint(equalTo: letter.widthAnchor).isActive = true }
                first.widthAnchor.constraint(equalTo: letter.widthAnchor, multiplier: 1.4).isActive = true
                last.widthAnchor.constraint(equalTo: letter.widthAnchor, multiplier: 1.4).isActive = true
            } else if let first = keys.first {
                for key in keys.dropFirst() { key.widthAnchor.constraint(equalTo: first.widthAnchor).isActive = true }
            }
            rows.addArrangedSubview(index == 1 && page == .letters ? Self.inset(row) : row)
        }
        // Bottom row: layer switch, globe (when the system needs one), space, return.
        let bottom = UIStackView()
        bottom.spacing = 6
        let layerKey = Self.key(page == .letters ? "123" : "ABC", dark: true)
        layerKey.addAction(UIAction { [weak self] _ in self?.switchTo(self?.page == .letters ? .numbers : .letters) }, for: .touchUpInside)
        let space = Self.key("space")
        space.accessibilityLabel = "Space"
        space.addAction(UIAction { [weak self] _ in self?.typed(" ") }, for: .touchUpInside)
        let returnKey = Self.key("return", dark: true)
        returnKey.addAction(UIAction { [weak self] _ in self?.onReturn?() }, for: .touchUpInside)
        bottom.addArrangedSubview(layerKey)
        if showsGlobe { bottom.addArrangedSubview(globe) }
        bottom.addArrangedSubview(space)
        bottom.addArrangedSubview(returnKey)
        layerKey.widthAnchor.constraint(equalToConstant: 48).isActive = true
        returnKey.widthAnchor.constraint(equalToConstant: 88).isActive = true
        rows.addArrangedSubview(bottom)
    }

    private static func inset(_ row: UIStackView) -> UIView {
        let holder = UIView()
        row.translatesAutoresizingMaskIntoConstraints = false
        holder.addSubview(row)
        NSLayoutConstraint.activate([
            row.topAnchor.constraint(equalTo: holder.topAnchor), row.bottomAnchor.constraint(equalTo: holder.bottomAnchor),
            row.centerXAnchor.constraint(equalTo: holder.centerXAnchor), row.widthAnchor.constraint(equalTo: holder.widthAnchor, multiplier: 0.9),
        ])
        return holder
    }

    static func key(_ title: String, symbol: Bool = false, dark: Bool = false) -> UIButton {
        var configuration = UIButton.Configuration.filled()
        configuration.baseBackgroundColor = dark || symbol ? .systemGray3 : .systemBackground
        configuration.baseForegroundColor = .label
        configuration.cornerStyle = .medium
        configuration.contentInsets = .init(top: 0, leading: 0, bottom: 0, trailing: 0)
        if symbol { configuration.image = UIImage(systemName: title) } else {
            configuration.attributedTitle = AttributedString(title, attributes: AttributeContainer([.font: UIFont.systemFont(ofSize: title.count == 1 ? 22 : 15)]))
        }
        let button = UIButton(configuration: configuration)
        button.layer.shadowColor = UIColor.black.cgColor
        button.layer.shadowOpacity = 0.25
        button.layer.shadowOffset = CGSize(width: 0, height: 1)
        button.layer.shadowRadius = 0
        return button
    }

    private func typed(_ text: String) {
        onText?(text)
        if shift == .once, page == .letters, text != " " { shift = .off }
    }
    private func toggleShift() { shift = shift == .off ? .once : shift == .once ? .locked : .off }
    private func switchTo(_ page: Page?) { guard let page else { return }; self.page = page; rebuild() }

    private func startDeleting() {
        onDelete?()
        deleteTimer?.invalidate()
        deleteTimer = Timer.scheduledTimer(withTimeInterval: 0.45, repeats: false) { [weak self] _ in
            MainActor.assumeIsolated {
                self?.deleteTimer = Timer.scheduledTimer(withTimeInterval: 0.08, repeats: true) { _ in MainActor.assumeIsolated { self?.onDelete?() } }
            }
        }
    }
    private func stopDeleting() { deleteTimer?.invalidate(); deleteTimer = nil }

    /// Back to letters after a space or return in the numbers layer, as the system keyboard does.
    func returnToLetters() { if page != .letters { switchTo(.letters) } }
}
