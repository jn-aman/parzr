"""Relative clauses: "who" for a thing ("the file who contains"), "whom" for a thing, and a pronoun that repeats the
relative word ("the book that I bought it").

"who" is matched only after a plainly inanimate noun that is not a person's job or a place standing for people
(no server, driver, agent, bot, model, company, team, shop, school, hotel). The verb after "who" must be an auxiliary
or a plain -s / -ed verb, so an indirect question ("tell the file who ...") never reads as a relative clause.
"""
from core import add, not_in, START, W

SEC = 'Relative clauses'

DET = r"(?:the|a|an|this|that|these|those|every|each|any|another|one|some|my|your|our|their|his|her|its)"
ADJ = r"(?:[a-z'’-]+ )?"
VERB = (r"(?:is|are|was|were|has|have|had|can|could|will|would|does|do|did|should|must|may|might|keeps|runs|contains|"
        r"handles|stores|shows|lets|helps|allows|makes|gives|provides|sends|supports|works|needs|takes|crashes|fails|"
        r"checks|manages|controls|creates|generates|processes|loads|reads|writes|opens|saves|runs|stops|starts|blocks|"
        r"broke|came|went|ran|took|made|gave|got|held|kept|left|lost|met|paid|sent|sold|spent|stood|told|threw|wrote|froze|fell|grew|began|became|caught|cost|hit|put|set|shut|fit|[a-z]+ed|[a-z]+s)\b")


def plural(stems):
    out = []
    for s in stems:
        out.append(s)
        if s.endswith(('s', 'sh', 'ch', 'x')):
            out.append(s + 'es')
        elif s.endswith('y') and s[-2] not in 'aeiou':
            out.append(s[:-1] + 'ies')
        elif not s.endswith('ware') and s not in ('software', 'code', 'hardware'):
            out.append(s + 's')
    return out


GROUPS = [
    ('documents', ['file', 'document', 'report', 'email', 'message', 'letter', 'page', 'article', 'book', 'spreadsheet',
                   'form', 'folder', 'photo', 'image', 'invoice', 'contract', 'newsletter', 'manual', 'chapter', 'note'],
     'I attached the report who summarizes the quarterly results.',
     'I attached the report that summarizes the quarterly results.',
     'I attached the report that summarizes the quarterly results. The author who wrote the report is away. Ask the clerk who filed the form.'),
    ('software', ['software', 'program', 'script', 'tool', 'app', 'application', 'plugin', 'feature', 'function', 'module',
                  'library', 'extension', 'website', 'database', 'platform', 'update', 'browser', 'algorithm'],
     'We deployed a script who removes old logs every night.',
     'We deployed a script that removes old logs every night.',
     'We deployed a script that removes old logs every night. The engineer who wrote the script is on leave. Ask the admin who runs the database.'),
    ('devices', ['device', 'machine', 'computer', 'laptop', 'phone', 'printer', 'router', 'tablet', 'camera', 'keyboard',
                 'screen', 'charger'],
     'She bought a laptop who has a much faster chip.',
     'She bought a laptop that has a much faster chip.',
     'She bought a laptop that has a much faster chip. The technician who fixed the printer left. Ask the girl who owns the camera.'),
    ('problems', ['bug', 'error', 'issue', 'problem', 'mistake', 'glitch', 'failure', 'crash', 'delay', 'outage'],
     'There is a bug who crashes the app on startup.',
     'There is a bug that crashes the app on startup.',
     'There is a bug that crashes the app on startup. The tester who found the bug is new. Tell the team who owns the issue.'),
    ('places', ['building', 'house', 'room', 'street', 'road', 'bridge', 'city', 'town', 'village', 'mountain', 'river',
                'lake', 'park', 'garden'],
     'We rented a house who has a view of the lake.',
     'We rented a house that has a view of the lake.',
     'We rented a house that has a view of the lake. The agent who showed the house was kind. Ask the owner who lives in the village.'),
    ('vehicles', ['car', 'bus', 'train', 'plane', 'truck', 'bike', 'bicycle', 'boat', 'ship'],
     'He sold the car who broke down twice last winter.',
     'He sold the car that broke down twice last winter.',
     'He sold the car that broke down twice last winter. The mechanic who fixed the car is local. Ask the driver who parked the truck.'),
    ('objects', ['table', 'chair', 'door', 'window', 'box', 'bag', 'bottle', 'key', 'bed', 'desk', 'lamp', 'shelf', 'coat',
                 'shirt', 'dress', 'shoe', 'dish', 'meal', 'cake', 'pizza', 'recipe'],
     'Please move the table who blocks the door.',
     'Please move the table that blocks the door.',
     'Please move the table that blocks the door. The man who owns the table is out. Ask the porter who carried the box.'),
]
# the noun phrase must not sit inside a prepositional phrase ("a user of a computer who ..." is about the user), so it
# follows a sentence start, a comma, or one of these verbs and linking words
PRE = (r"(?:" + START + r"|,\s+|\b(?:is|are|was|were|has|have|had|having|there|buy|bought|sell|sold|find|found|"
       r"make|made|write|wrote|build|built|install|installed|attach|attached|attaching|deploy|deployed|receive|received|send|"
       r"sent|use|used|using|open|opened|read|fix|fixed|check|checked|create|created|need|needed|want|wanted|see|saw|get|got|"
       r"take|took|move|moved|remove|removed|delete|deleted|update|updated|download|downloaded|upload|uploaded|save|saved|"
       r"print|printed|share|shared|choose|chose|pick|picked|try|tried|test|tested|replace|replaced|review|reviewed|and|but|"
       r"or|if|when|while|where|that|because|so|then|just|only|also|still|rent|rented|own|owned|repair|repaired|park|parked|"
       r"drive|drove|order|ordered|cook|cooked|eat|ate|carry|carried|lift|lifted|clean|cleaned|paint|painted|sign|signed)\s+)")
for key, stems, pos, fixed, neg in GROUPS:
    nouns = '|'.join(plural(stems))
    add('who_for_thing.' + key,
        r"(?im)" + PRE + DET + r" " + ADJ + r"(?-i:" + nouns + r") (?P<target>who) " + VERB,
        'that', 'Grammar', 0.9,
        '“Who” is for people; use “that” (or “which”) for a thing.',
        pos, neg, fixed, SEC)

add('who_for_thing.whom',
    r"(?im)" + PRE + DET + r" " + ADJ + r"(?-i:" + '|'.join(plural([s for _, st, _, _, _ in GROUPS for s in st])) + r") (?P<target>whom) (?:I|we|you|he|she|they)\b",
    'which', 'Grammar', 0.9,
    '“Whom” is for people; use “which” (or “that”) for a thing.',
    'This is the report whom I mentioned in the meeting.',
    'This is the report which I mentioned in the meeting. This is the author whom I mentioned in the meeting. To whom did you send the report?',
    'This is the report which I mentioned in the meeting.', SEC)

# ---- a pronoun that repeats the relative word -----------------------------------------------------------------------------
PRON = r"(?:I|we|you|he|she|they)"
HEAD_DET = r"(?:the|this|that|my|your|our|their|his|her|these|those)"
RES = [
    ('it_media', 'it', ['book', 'movie', 'film', 'song', 'article', 'video', 'game', 'show', 'series', 'podcast', 'novel', 'poem'],
     'This is the song that I wrote it.', 'This is the song that I wrote.',
     'This is the song that I wrote. This is the song that I wrote for her. This is the song that I like. I wrote it.'),
    ('it_objects', 'it', ['car', 'phone', 'laptop', 'shirt', 'dress', 'gift', 'ring', 'watch', 'bag', 'camera', 'bike', 'jacket'],
     'That is the jacket which she bought it.', 'That is the jacket which she bought.',
     'That is the jacket which she bought. That is the jacket which she bought in Milan. She bought it in Milan.'),
    ('it_food', 'it', ['food', 'dish', 'meal', 'cake', 'pizza', 'soup', 'coffee', 'recipe', 'sandwich', 'curry'],
     'This is the curry that we ordered it.', 'This is the curry that we ordered.',
     'This is the curry that we ordered. This is the curry that we ordered for lunch. We ordered it for lunch.'),
    ('it_software', 'it', ['app', 'program', 'tool', 'file', 'script', 'plugin', 'website', 'game'],
     'This is the tool that we built it.', 'This is the tool that we built.',
     'This is the tool that we built. This is the tool that we built it with. We built it last year.'),
    ('them_media', 'them', ['books', 'movies', 'films', 'songs', 'articles', 'videos', 'games', 'shows', 'novels', 'poems'],
     'These are the books that I borrowed them.', 'These are the books that I borrowed.',
     'These are the books that I borrowed. These are the books that I borrowed from her. I borrowed them yesterday.'),
    ('them_things', 'them', ['cars', 'phones', 'laptops', 'shirts', 'gifts', 'rings', 'bags', 'cameras', 'files', 'tools', 'apps', 'recipes'],
     'Those are the files which they sent them.', 'Those are the files which they sent.',
     'Those are the files which they sent. Those are the files which they sent to us. They sent them today.'),
]
for key, pro, nouns, pos, fixed, neg in RES:
    add('resumptive.' + key,
        r"(?i)\b" + HEAD_DET + r" (?:[a-z'’-]+ )?(?:" + '|'.join(nouns) + r") (?:that|which|whom) " + PRON + r" [a-z'’]+(?P<target> " + pro + r")[.!?]",
        '', 'Grammar', 0.88,
        'The relative word already stands for the thing, so the pronoun “' + pro + '” repeats it.',
        pos, neg, fixed, SEC)
