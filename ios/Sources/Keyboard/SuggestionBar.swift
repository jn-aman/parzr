import UIKit
import ParzrKit

/// The strip above the keys: the current sentence's corrections, then tone rewrites, or a
/// message (a rewrite being written, handed to the app, or ready to use).
final class SuggestionBar: UIView {
    var onSuggestion: ((Suggestion) -> Void)?
    var onFixAll: (() -> Void)?
    var onTone: ((RewriteMode) -> Void)?
    var onAction: (() -> Void)?

    private let stack = UIStackView()
    private var showingTones = false

    override init(frame: CGRect) {
        super.init(frame: frame)
        stack.axis = .horizontal
        stack.spacing = 6
        stack.alignment = .center
        stack.translatesAutoresizingMaskIntoConstraints = false
        addSubview(stack)
        NSLayoutConstraint.activate([
            stack.leadingAnchor.constraint(equalTo: leadingAnchor, constant: 6),
            stack.trailingAnchor.constraint(lessThanOrEqualTo: trailingAnchor, constant: -6),
            stack.topAnchor.constraint(equalTo: topAnchor, constant: 4),
            stack.bottomAnchor.constraint(equalTo: bottomAnchor, constant: -4),
        ])
        show(suggestions: [], fixAll: false)
    }
    required init?(coder: NSCoder) { fatalError("init(coder:) is not used") }

    func show(suggestions: [Suggestion], fixAll: Bool) {
        guard !showingTones else { return }
        clear()
        for suggestion in suggestions {
            let button = Self.chip(suggestion.title, prominent: true)
            button.accessibilityLabel = "\(suggestion.category): \(suggestion.detail)"
            button.addAction(UIAction { [weak self] _ in self?.onSuggestion?(suggestion) }, for: .touchUpInside)
            stack.addArrangedSubview(button)
        }
        if fixAll {
            let all = Self.chip("Fix all", prominent: false)
            all.addAction(UIAction { [weak self] _ in self?.onFixAll?() }, for: .touchUpInside)
            stack.addArrangedSubview(all)
        }
        if suggestions.isEmpty { stack.addArrangedSubview(Self.label("Parzr")) }
        let tones = Self.chip("Rewrite", symbol: "wand.and.sparkles", prominent: false)
        tones.addAction(UIAction { [weak self] _ in self?.showTones() }, for: .touchUpInside)
        stack.addArrangedSubview(tones)
    }

    private func showTones() {
        clear()
        showingTones = true
        for mode in RewriteMode.allCases where mode != .fix {
            let button = Self.chip(mode.title, symbol: mode.symbol, prominent: false)
            button.accessibilityHint = mode.help
            button.addAction(UIAction { [weak self] _ in self?.showingTones = false; self?.onTone?(mode) }, for: .touchUpInside)
            stack.addArrangedSubview(button)
        }
        stack.addArrangedSubview(closeButton())
    }

    /// A message, with an optional action ("Use Professional version").
    func show(message: String, action: String? = nil) {
        showingTones = false
        clear()
        if let action {
            let button = Self.chip(action, prominent: true)
            button.addAction(UIAction { [weak self] _ in self?.onAction?() }, for: .touchUpInside)
            stack.addArrangedSubview(button)
        }
        stack.addArrangedSubview(Self.label(message))
        stack.addArrangedSubview(closeButton())
    }

    private func closeButton() -> UIButton {
        let close = Self.chip("", symbol: "xmark", prominent: false)
        close.accessibilityLabel = "Close"
        close.addAction(UIAction { [weak self] _ in self?.showingTones = false; self?.onAction = nil; self?.show(suggestions: [], fixAll: false); self?.onClose?() }, for: .touchUpInside)
        return close
    }
    var onClose: (() -> Void)?

    private func clear() { stack.arrangedSubviews.forEach { $0.removeFromSuperview() } }

    private static func chip(_ title: String, symbol: String? = nil, prominent: Bool) -> UIButton {
        var configuration = prominent ? UIButton.Configuration.filled() : UIButton.Configuration.gray()
        configuration.cornerStyle = .capsule
        configuration.title = title.isEmpty ? nil : title
        configuration.image = symbol.flatMap { UIImage(systemName: $0) }
        configuration.imagePadding = 4
        configuration.titleLineBreakMode = .byTruncatingTail
        configuration.contentInsets = .init(top: 4, leading: 10, bottom: 4, trailing: 10)
        let button = UIButton(configuration: configuration)
        button.setContentCompressionResistancePriority(.defaultHigh, for: .horizontal)
        return button
    }

    private static func label(_ text: String) -> UILabel {
        let label = UILabel()
        label.text = text
        label.font = .preferredFont(forTextStyle: .footnote)
        label.textColor = .secondaryLabel
        label.numberOfLines = 2
        label.adjustsFontSizeToFitWidth = true
        label.minimumScaleFactor = 0.8
        label.setContentCompressionResistancePriority(.defaultLow, for: .horizontal)
        return label
    }
}
