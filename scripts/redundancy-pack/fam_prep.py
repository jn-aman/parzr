"""Doubled prepositions: "off of", "alongside of", "atop of", "where is the bathroom at", "where are you going to"."""
from core import add, style, S, E

SEC = 'Doubled prepositions'
# "off of" stays when "of" starts the next phrase ("off of course" is "off, of course").
OBJ = (r"(?:the|a|an|his|her|their|my|our|your|its|this|that|these|those|him|them|me|us|you|it|each|every|any|some|all|"
       r"one|two|three|\d+|(?-i:[A-Z][a-z]+))")
PLACES = ('bathroom|restroom|toilet|station|library|bank|hospital|school|office|store|shop|market|pharmacy|airport|'
          'post office|exit|entrance|elevator|lift|stairs|kitchen|lobby|cafeteria|gym|pool|park|museum|church|temple|'
          'mosque|bus stop|parking lot|car park|taxi stand|ticket counter|meeting room|conference room|waiting room')
MOTION = ('go|going|goes|went|gone|headed|heading|run|ran|running|move|moving|moved|walk|walked|walking|drive|driving|'
          'drove|fly|flying|flew|travel|travelling|traveling|travelled|traveled|come|coming|came')


def build():
    ids = []
    ids.append(add('prep.off_of', rf'(?im){S}(?P<target>off of) {OBJ}{E}', 'off', 'Style', 0.8,
                   '“Off of” has one preposition too many: say “off”.',
                   'He fell off of the roof.',
                   'He fell off the roof, and the best of the lot kept off the grass. He set off, of course.'))
    ids.append(add('prep.alongside_of', rf'(?im){S}(?P<target>alongside of) {OBJ}{E}', 'alongside', 'Style', 0.8,
                   '“Alongside” is a preposition already: drop “of”.',
                   'The path runs alongside of the river.',
                   'The path runs alongside the river, and the best of the cafes is at the end.'))
    ids.append(add('prep.atop_of', rf'(?im){S}(?P<target>atop of) {OBJ}{E}', 'atop', 'Grammar', 0.85,
                   '“Atop” is a preposition already: drop “of”.',
                   'The flag sits atop of the tower.',
                   'The flag sits atop the tower, and on top of that a light shines.'))
    ids.append(add('prep.where_place_at',
                   rf'(?im){S}where(?:[’\']s| is| are| was| were) (?:the |my |your |our |their |his |her )?(?:{PLACES})(?P<target> at)(?:[.!?,;]|$)',
                   '', 'Grammar', 0.8,
                   '“Where” already asks for the place: drop the extra “at”.',
                   'Where is the bathroom at?',
                   'Where is the bathroom? Look at the sign. Where is the bank at the corner of the street?'))
    ids.append(add('prep.where_going_to',
                   rf'(?im){S}where (?:are|is|was|were|am|did|do|does|will|would|can|should|could|has|have|had) (?:you|he|she|they|we|I|it|the \w+) (?:{MOTION})(?P<target> to)(?:[.!?,;]|$)',
                   '', 'Style', 0.76,
                   '“Where” already asks for the place: drop the extra “to”.',
                   'Where are you going to?',
                   'Where are you going? Where are you going to eat, and where do I go to get tickets?'))
    return ids
