"""Spaces and doubled marks inside contractions ("do n't", "it 's", "don''t")."""
import core

AP = r"['’]"


def build():
    # "do n't" -> "don't"
    for aux, fixed, subj, tail in (
            ('do', "don't", 'We', 'know yet'), ('does', "doesn't", 'She', 'know yet'), ('did', "didn't", 'We', 'know yet'),
            ('is', "isn't", 'She', 'ready yet'), ('are', "aren't", 'We', 'ready yet'), ('was', "wasn't", 'She', 'ready yet'),
            ('were', "weren't", 'We', 'ready yet'), ('have', "haven't", 'We', 'seen it yet'),
            ('has', "hasn't", 'She', 'seen it yet'), ('had', "hadn't", 'We', 'seen it yet'),
            ('would', "wouldn't", 'We', 'know yet'), ('could', "couldn't", 'We', 'know yet'),
            ('should', "shouldn't", 'We', 'know yet'), ('must', "mustn't", 'We', 'know yet'),
            ('need', "needn't", 'We', 'know yet')):
        core.add(f'contraction.{aux}_n_t', rf'(?i)\b{aux}(?P<target> )n{AP}t\b', '', 'Punctuation', 0.95,
                 f'Remove the space inside “{fixed}”.', f"{subj} {aux} n't {tail}.",
                 f"{subj} {fixed} {tail}. The {aux} notes were useful.", f"{subj} {fixed} {tail}.")
    core.add('contraction.ca_n_t', rf"(?i)\b(?:we|you|they|he|she|it|I|who|that|there)\s+ca(?P<target> )n{AP}t\b", '',
             'Punctuation', 0.95, 'Remove the space inside “can’t”.', "We ca n't see it yet.",
             "We can't see it yet.")
    core.add('contraction.wo_n_t', rf"(?i)\b(?:we|you|they|he|she|it|I|who|that|there)\s+wo(?P<target> )n{AP}t\b", '',
             'Punctuation', 0.95, 'Remove the space inside “won’t”.', "We wo n't see it yet.",
             "We won't see it yet.")
    # "it 's" -> "it's"
    for subj in ('it', 'he', 'she', 'that', 'there', 'here', 'what', 'who', 'where', 'how', 'let'):
        core.add(f'contraction.{subj}_s', rf'(?i)\b{subj}(?P<target> ){AP}s\b', '', 'Punctuation', 0.94,
                 f'Remove the space inside “{subj}’s”.', f"{subj.capitalize()} 's a good point.",
                 f"{subj.capitalize()}'s a good point. The {subj} sign was bent.",
                 f"{subj.capitalize()}'s a good point.")
    tails = {'m': 'here now', 're': 'here now', 'll': 'call you', 've': 'been here', 'd': 'like that'}
    for pron, tail, word in (('I', 'm', "I'm"), ('I', 'll', "I'll"), ('I', 've', "I've"), ('I', 'd', "I'd"),
                             ('you', 're', "you're"), ('we', 're', "we're"), ('they', 're', "they're"),
                             ('you', 'll', "you'll"), ('we', 'll', "we'll"), ('they', 'll', "they'll"),
                             ('you', 've', "you've"), ('we', 've', "we've"), ('they', 've', "they've"),
                             ('you', 'd', "you'd"), ('we', 'd', "we'd"), ('they', 'd', "they'd")):
        P = pron if pron == 'I' else pron.capitalize()
        w = word if pron == 'I' else word.capitalize()
        core.add(f'contraction.{pron.lower()}_{tail}', rf'(?i)\b{pron}(?P<target> ){AP}{tail}\b', '', 'Punctuation', 0.94,
                 f'Remove the space inside “{word}”.', f"{P} '{tail} {tails[tail]}.",
                 f"{w} {tails[tail]}. The {pron} sign was bent.", f"{w} {tails[tail]}.")
    # "don''t" -> "don't"
    core.add('apostrophe.doubled_straight', r"(?i)\b[a-z]+(?P<target>'')(?:t|s|re|ve|ll|d|m)\b", "'", 'Punctuation', 0.94,
             'Use a single apostrophe.', "We don''t know yet.", "We don't know yet.", "We don't know yet.")
    core.add('apostrophe.doubled_curly', r"(?i)\b[a-z]+(?P<target>’’)(?:t|s|re|ve|ll|d|m)\b", "’", 'Punctuation', 0.94,
             'Use a single apostrophe.', "We don’’t know yet.", "We don’t know yet.", "We don’t know yet.")
