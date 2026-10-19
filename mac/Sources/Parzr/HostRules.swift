import Foundation

/// Per-app and per-field rules for automatic checking, and the sensitive-field keywords that keep it out of passwords, one-time codes,
/// search boxes, addresses and other form fields that hold no prose. Data, not code: Parzr's own built-in list below, plus an optional
/// `~/Library/Application Support/Parzr/HostRules.json` in the same format, read once. Rules only ever block or lift the keyword list;
/// they never make a field writable, searchable fields checkable, or a secure field readable (see `Compat.editorEligibility`).
struct HostRules: Decodable {
    struct Rule: Decodable {
        var id: String
        /// Regular expressions, matched case-insensitively; a rule applies when every one it has matches.
        var bundle: String?
        var url: String?
        /// Matched against the field's labels, identifiers and DOM classes (and its ancestors' with `ancestors`).
        var element: String?
        var ancestors: Bool?
        /// true: only single-line text fields; false: only multi-line editors; absent: both.
        var singleLine: Bool?
        /// false: never check automatically.
        var enabled: Bool?
        /// false: skip single-line text fields in this host (multi-line editors stay checked).
        var textFields: Bool?
        /// true: the sensitive keywords below do not apply (a host whose composer's name happens to contain one).
        var ignoreSensitive: Bool?
        var note: String?
    }
    struct Keyword: Decodable {
        var id: String
        var pattern: String
        /// Only single-line text fields: a form's "City" box, never a message body that mentions a city.
        var singleLine: Bool?
        /// Also look at the field's ancestors (a sign-in form, a checkout page section).
        var ancestors: Bool?
    }
    var rules: [Rule]
    var sensitive: [Keyword]

    /// What Parzr knows about one focused field, read by `AX.fieldContext`. Labels are the field's own placeholder, description, title,
    /// identifier and DOM identifier; markers add its DOM classes. `ancestors` holds the same, nearest first, up to the web area or window.
    struct Field: Equatable {
        var bundle: String?
        var url: String?
        var role: String?
        var labels: [String] = []
        var markers: [String] = []
        var ancestors: [[String]] = []
        var singleLine: Bool { role == "AXTextField" }
    }
    enum Verdict: Equatable { case allowed, blocked(String) }

    func verdict(for field: Field) -> Verdict {
        let own = field.labels + field.markers, around = field.ancestors.flatMap { $0 }
        let matching = compiledRules.filter { rule in
            (rule.singleLine.map { $0 == field.singleLine } ?? true) && (rule.bundle.map { Self.matches($0, field.bundle) } ?? true) && (rule.url.map { Self.matches($0, field.url) } ?? true)
                && (rule.element.map { pattern in (own + (rule.ancestors == true ? around : [])).contains { Self.matches(pattern, $0) } } ?? true)
        }
        if let off = matching.first(where: { $0.enabled == false }) { return .blocked("rule:\(off.id)") }
        if field.singleLine, let off = matching.first(where: { $0.textFields == false }) { return .blocked("rule:\(off.id)") }
        guard !matching.contains(where: { $0.ignoreSensitive == true }) else { return .allowed }
        for keyword in compiledKeywords where keyword.singleLine != true || field.singleLine {
            let labels = field.labels + (keyword.ancestors == true ? around : [])
            if labels.contains(where: { Self.matches(keyword.pattern, $0) }) { return .blocked("sensitive:\(keyword.id)") }
        }
        return .allowed
    }
    /// A whole app is off (a bundle rule with nothing else to match): the observer never attaches to it.
    func excludesApp(_ bundle: String?) -> Bool {
        compiledRules.contains { $0.enabled == false && $0.singleLine == nil && $0.url == nil && $0.element == nil && $0.bundle.map { Self.matches($0, bundle) } == true }
    }

    // MARK: Matching

    private var compiledRules: [CompiledRule] { cache.rules }
    private var compiledKeywords: [CompiledKeyword] { cache.keywords }
    private let cache: Cache
    private enum CodingKeys: String, CodingKey { case rules, sensitive }
    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        rules = try container.decodeIfPresent([Rule].self, forKey: .rules) ?? []
        sensitive = try container.decodeIfPresent([Keyword].self, forKey: .sensitive) ?? []
        cache = try Cache(rules: rules, sensitive: sensitive)
    }
    init(rules: [Rule], sensitive: [Keyword]) throws {
        self.rules = rules; self.sensitive = sensitive
        cache = try Cache(rules: rules, sensitive: sensitive)
    }
    /// Both lists together: the user's file adds to the built-in one, never replaces it.
    func merged(with other: HostRules) -> HostRules { (try? HostRules(rules: rules + other.rules, sensitive: sensitive + other.sensitive)) ?? self }

    struct CompiledRule {
        let id: String, bundle: NSRegularExpression?, url: NSRegularExpression?, element: NSRegularExpression?
        let ancestors: Bool?, singleLine: Bool?, enabled: Bool?, textFields: Bool?, ignoreSensitive: Bool?
    }
    struct CompiledKeyword { let id: String, pattern: NSRegularExpression, singleLine: Bool?, ancestors: Bool? }
    private final class Cache: @unchecked Sendable {
        let rules: [CompiledRule], keywords: [CompiledKeyword]
        init(rules: [Rule], sensitive: [Keyword]) throws {
            func regex(_ pattern: String?) throws -> NSRegularExpression? { try pattern.map { try NSRegularExpression(pattern: $0, options: [.caseInsensitive]) } }
            self.rules = try rules.map { CompiledRule(id: $0.id, bundle: try regex($0.bundle), url: try regex($0.url), element: try regex($0.element), ancestors: $0.ancestors, singleLine: $0.singleLine, enabled: $0.enabled, textFields: $0.textFields, ignoreSensitive: $0.ignoreSensitive) }
            keywords = try sensitive.map { CompiledKeyword(id: $0.id, pattern: try NSRegularExpression(pattern: $0.pattern, options: [.caseInsensitive]), singleLine: $0.singleLine, ancestors: $0.ancestors) }
        }
    }
    private static func matches(_ pattern: NSRegularExpression, _ value: String?) -> Bool {
        guard let value, !value.isEmpty else { return false }
        return pattern.firstMatch(in: value, range: NSRange(location: 0, length: (value as NSString).length)) != nil
    }

    // MARK: Loading

    static let builtIn: HostRules = {
        do { return try JSONDecoder().decode(HostRules.self, from: Data(builtInJSON.utf8)) } catch { preconditionFailure("Built-in host rules do not parse: \(error)") }
    }()
    /// The built-in rules plus the user's file, if there is one and it parses; a broken file is ignored rather than turning checking off.
    static let shared: HostRules = {
        guard let support = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask).first,
              let data = try? Data(contentsOf: support.appendingPathComponent("Parzr/HostRules.json")), data.count <= 262_144,
              let user = try? JSONDecoder().decode(HostRules.self, from: data) else { return builtIn }
        return builtIn.merged(with: user)
    }()

    /// Parzr's own list. Word boundaries keep "pin" out of "spinning" and "otp" out of "footprint".
    static let builtInJSON = #"""
    {
      "rules": [
        {"id": "page-opt-out", "element": "^parzr-disable$", "ancestors": true, "enabled": false, "note": "A web page or app marks a field (or a container) as not for Parzr."},
        {"id": "page-opt-in", "element": "^parzr-enable$", "ancestors": true, "ignoreSensitive": true, "note": "Lifts the keyword list only; writable, search and secure checks still apply."},
        {"id": "password-managers", "bundle": "^(com\\.1password\\.|com\\.agilebits\\.|com\\.bitwarden\\.|org\\.keepassxc\\.|com\\.lastpass\\.|com\\.dashlane\\.|me\\.proton\\.pass|ch\\.protonmail\\.pass|in\\.sinew\\.enpass|com\\.nordsec\\.nordpass|com\\.keepersecurity\\.|com\\.callpod\\.keeper|com\\.siber\\.roboform|com\\.markmcguill\\.strongbox|com\\.hicknhacksoftware\\.macpass|com\\.keepassium\\.|com\\.zetetic\\.codebook|com\\.outercorner\\.secrets|com\\.apple\\.Passwords|com\\.apple\\.keychainaccess$)", "enabled": false, "note": "Password managers (1Password in every edition, Bitwarden, Dashlane, LastPass, KeePassXC, Proton Pass, Enpass, NordPass, Keeper, RoboForm, Strongbox, MacPass, KeePassium, Codebook, Secrets, Apple Passwords and Keychain Access): never read, never copied from."},
        {"id": "authenticators", "bundle": "^(com\\.authy\\.|com\\.twilio\\.authy|io\\.ente\\.auth|com\\.bitwarden\\.authenticator)", "enabled": false, "note": "One-time-code apps."},
        {"id": "system-security", "bundle": "^(com\\.apple\\.SecurityAgent|com\\.apple\\.loginwindow|com\\.apple\\.systempreferences|com\\.apple\\.Settings)", "enabled": false, "note": "Login, unlock and settings panes hold no prose."},
        {"id": "browser-address-bars", "bundle": "^(com\\.apple\\.Safari|com\\.google\\.Chrome|com\\.microsoft\\.edgemac|com\\.brave\\.Browser|company\\.thebrowser\\.Browser|org\\.mozilla\\.)", "element": "^(address|url|location|omnibox)", "enabled": false},
        {"id": "url-sign-in", "url": "^https?://(www\\.)?(accounts?|login|signin|auth|sso)\\.", "enabled": false, "note": "Sign-in and account hosts (accounts.example.com, login.example.com)."},
        {"id": "url-auth-path", "url": "^https?://[^/]+/([^?#]*/)?(login|signin|sign-in|sign_in|signup|sign-up|auth|oauth|2fa|mfa|verify|checkout|payment|billing)(/|$|\\?|#)", "enabled": false},
        {"id": "chat-and-mail-composers", "bundle": "^(com\\.tinyspeck\\.slackmacgap|com\\.microsoft\\.teams2?|com\\.hnc\\.Discord|com\\.apple\\.MobileSMS|com\\.apple\\.mail|com\\.apple\\.Notes|com\\.microsoft\\.Outlook|net\\.whatsapp\\.WhatsApp|ru\\.keepcoder\\.Telegram)$", "singleLine": false, "ignoreSensitive": true, "note": "Composer placeholders name the channel or person (\"Message #password-reset\")."},
        {"id": "web-chat-and-mail-composers", "url": "^https://(app\\.slack\\.com|mail\\.google\\.com|teams\\.microsoft\\.com|teams\\.live\\.com|outlook\\.(live|office|office365)\\.com|discord\\.com|web\\.whatsapp\\.com)/", "singleLine": false, "ignoreSensitive": true}
      ],
      "sensitive": [
        {"id": "password", "pattern": "pass(word|code|phrase)|\\bpasswd\\b|\\bpwd\\b|\\bpin\\b|contrase(ñ|n)a|mot de passe|passwort|kennwort|\\bsenha\\b"},
        {"id": "one-time-code", "pattern": "\\botp\\b|\\btotp\\b|\\bmfa\\b|\\b2fa\\b|two[- ]?factor|one[- ]?time (code|password|pin)|verification code|security code|confirmation code|auth(entication|orization)? code|\\bsms code\\b|código de verificación|code de vérification|bestätigungscode"},
        {"id": "payment", "pattern": "credit card|card number|card holder|cardholder|\\bcvv\\b|\\bcvc\\b|\\bcsc\\b|expir(y|ation|es)|\\biban\\b|routing number|account number|sort code"},
        {"id": "identity", "pattern": "\\bssn\\b|social security|tax id|\\btin\\b|\\bein\\b|passport|driver'?s? licen[cs]e|date of birth|\\bdob\\b|birth ?date"},
        {"id": "secret", "pattern": "\\bsecret\\b|api[- _]?key|access[- _]?token|private key|recovery (code|phrase|key)|seed phrase"},
        {"id": "email-address", "pattern": "\\S+@\\S+\\.\\S+", "singleLine": true},
        {"id": "search", "pattern": "^(find|filter|search|buscar|rechercher|suchen|cerca|pesquisar)\\b|\\b(search|filter)$", "singleLine": true},
        {"id": "contact", "pattern": "e-?mail|\\bphone\\b|telephone|\\bmobile\\b|\\bfax\\b|user ?name|user ?id|\\blogin\\b|\\burl\\b|website|^(to|cc|bcc|from)$", "singleLine": true},
        {"id": "address", "pattern": "\\baddress\\b|street|address line|\\bcity\\b|\\btown\\b|postal|post ?code|zip ?code|\\bzip\\b|\\bcountry\\b|\\bstate\\b|province|county|dirección|adresse|indirizzo|endereço", "singleLine": true},
        {"id": "person-name", "pattern": "^(first|last|full|middle|given|family|sur|nick|display|company|organi[sz]ation)?[ _-]?name$", "singleLine": true},
        {"id": "numbers", "pattern": "^(date|time|amount|price|quantity|qty|number|age|zip|code)$|\\bcoupon\\b|promo code|gift card", "singleLine": true},
        {"id": "sign-in-form", "pattern": "sign[- ]?in|log[- ]?in|sign[- ]?up|two[- ]?factor|\\b2fa\\b|authenticat|create (an )?account|reset (your )?password", "ancestors": true, "singleLine": true}
      ]
    }
    """#
}
