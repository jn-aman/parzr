"""A verb followed by a particle or adverb that its own meaning already contains: "return back", "join together",
"repeat again", "exit out", "descend down"."""
from core import verb, add, style, cover, note, S, E, AFTER_NOOF

SEC = 'Verb plus a particle it already contains'
# "again" may end the clause or lead into a new one, but "again and again" is the idiom and stays.
AGAIN_END = (r"(?:[^\w'’\s-]|\s*$|\s+(?:what|that|the|your|my|his|her|our|their|please|slowly|for|because|so|if|when|how|"
             r"where|why|to|in|on|at|with|before|after|but|next|this|later|soon|tomorrow|tonight|today|within|by|from|over|as|is|will)\b)")


def build():
    ids = []
    V = lambda *a, **k: ids.append(verb(*a, **k))
    V('verb.return_back', 'return', 'back',
      'Please return back to the lobby when the tour ends.',
      'Please return to the lobby. The back door is locked, and the return desk opens at nine.')
    V('verb.revert_back', 'revert', 'back',
      'The site will revert back to the old layout tonight.',
      'The site will revert to the old layout tonight, and the back office is closed.')
    V('verb.reply_back', 'reply', 'back',
      'Please reply back by Friday.',
      'Please reply by Friday. We will write back when the quote is ready.')
    V('verb.respond_back', 'respond', 'back',
      'I will respond back once I have the numbers.',
      'I will respond once I have the numbers, and then come back to the thread.')
    V('verb.restore_back', 'restore', 'back',
      'The backup will restore back your old settings.',
      'The backup will restore your old settings, and you can go back whenever you like.')
    V('verb.regain_back', 'regain', 'back',
      'She worked hard to regain back her strength.',
      'She worked hard to regain her strength, and then went back to the gym.')
    V('verb.rewind_back', 'rewind', 'back',
      'Rewind back the tape to the start.',
      'Rewind the tape to the start, then put it back in the box.')
    V('verb.retreat_back', 'retreat', 'back',
      'The army had to retreat back across the river.',
      'The army had to retreat across the river, and the back lines held.')
    V('verb.reclaim_back', 'reclaim', 'back',
      'They hope to reclaim back the land.',
      'They hope to reclaim the land, and the back field is already theirs.')
    V('verb.retrieve_back', 'retrieve', 'back',
      'Can you retrieve back the lost file?',
      'Can you retrieve the lost file? It is in the back folder.')
    V('verb.recover_back', 'recover', 'back',
      'We managed to recover back most of the money.',
      'We managed to recover most of the money, and the rest is on its way back.')
    V('verb.repeat_again', 'repeat', 'again',
      'Could you please repeat again what you said?',
      'Could you please repeat what you said? Say it again, slowly. Practice the move again and again.',
      guard=AGAIN_END)
    V('verb.reiterate_again', 'reiterate', 'again',
      'I want to reiterate again that the deadline is firm.',
      'I want to reiterate that the deadline is firm, and I will say it again on Monday.', guard=AGAIN_END)
    V('verb.recur_again', 'recur', 'again',
      'If the problem should recur again, call us.',
      'If the problem should recur, call us. Call us again if it does.', guard=AGAIN_END)
    V('verb.reoccur_again', 'reoccur', 'again',
      'The error may reoccur again next week.',
      'The error may reoccur next week, and we will check it again.', guard=AGAIN_END)
    V('verb.ascend_up', 'ascend', 'up(?:wards?)?',
      'The climbers ascend up the north face at dawn.',
      'The climbers ascend the north face at dawn, then walk up to the hut.')
    V('verb.descend_down', 'descend', 'down(?:wards?)?',
      'The path will descend down into the valley.',
      'The path will descend into the valley, and the road runs down to the sea.')
    V('verb.proceed_forward', 'proceed', 'forwards?',
      'We can proceed forward with the plan.',
      'We can proceed with the plan, and then move forward to phase two.')
    V('verb.progress_forward', 'progress', 'forward',
      'The talks may progress forward next week.',
      'The talks may progress next week, and the vote moves forward in May.',
      guard=E)
    V('verb.advance_forward', 'advance', 'forwards?',
      'The troops advance forward at first light.',
      'The troops advance at first light, and the rest move forward later.')
    V('verb.collaborate_together', 'collaborate', 'together',
      'The two teams will collaborate together on the launch.',
      'The two teams will collaborate on the launch, and then sit together for lunch.')
    V('verb.cooperate_together', r'co-?operate', 'together',
      'We hope the schools will cooperate together this year.',
      'We hope the schools will cooperate this year, and the pupils work together often.',
      phrase='cooperate together', kshow='cooperate')
    V('verb.combine_together', 'combine', 'together',
      'Combine together the flour and the sugar.',
      'Combine the flour and the sugar, then stir them together slowly.')
    ids.append(add('verb.join_together',
                   rf'(?im){S}(?:to|will|would|can|could|should|must|may|might|shall|please|let[’\']s|let us|and|or|not) (?P<target>(?P<v>join) together){E}',
                   '${v}', 'Style', 0.74,
                   '“join together” says the same thing twice: “join” is enough.',
                   'The two roads will join together near the bridge.',
                   'The two roads join near the bridge, and the villages sit close together. The two firms have joined together to bid.'))
    V('verb.merge_together', 'merge', 'together',
      'The two firms will merge together next spring.',
      'The two firms will merge next spring, and the staff will work together.')
    V('verb.unite_together', 'unite', 'together',
      'The parties vowed to unite together against the bill.',
      'The parties vowed to unite against the bill, and they marched together.')
    V('verb.unify_together', 'unify', 'together',
      'The new flag will unify together the regions.',
      'The new flag will unify the regions, and they will march together.')
    V('verb.consolidate_together', 'consolidate', 'together',
      'We will consolidate together the three reports.',
      'We will consolidate the three reports, and then review them together.')
    V('verb.assemble_together', 'assemble', 'together',
      'The crowd began to assemble together in the square.',
      'The crowd began to assemble in the square, and the band played together.')
    V('verb.converge_together', 'converge', 'together',
      'The two streams converge together below the falls.',
      'The two streams converge below the falls, and the fish swim together.')
    V('verb.congregate_together', 'congregate', 'together',
      'The birds congregate together at dusk.',
      'The birds congregate at dusk, and the chicks stay together.')
    V('verb.fuse_together', 'fuse', 'together',
      'The heat will fuse together the two plastic parts.',
      'The heat will fuse the two plastic parts, and the pieces stay together.')
    V('verb.coalesce_together', 'coalesce', 'together',
      'The small groups coalesce together into one movement.',
      'The small groups coalesce into one movement, and they march together.')
    V('verb.amalgamate_together', 'amalgamate', 'together',
      'The banks will amalgamate together next year.',
      'The banks will amalgamate next year, and the staff stay together.')
    V('verb.team_up_together', r'team(?:s|ed|ing)? up', 'together',
      'The two schools will team up together this year.',
      'The two schools will team up this year, and the pupils work together.',
      phrase='team up together', kshow='team up', forms='')
    ids.append(add('verb.protrude_out_of', rf'(?im){S}(?P<target>(?P<v>protrud(?:e|es|ed|ing)) out of){E}', '${v} from', 'Style', 0.78,
                   '“Protrude” already means to stick out: say “protrude from”, not “protrude out of”.',
                   'A nail will protrude out of the board.',
                   'A nail will protrude from the board, and the ends stick out of the box.'))
    V('verb.protrude_out', 'protrud(?:e|es|ed|ing)', 'out',
      'A nail may protrude out at the corner.',
      'A nail may protrude at the corner, and the ends stick out.', forms='', guard=AFTER_NOOF,
      phrase='protrude out', kshow='protrude')
    V('verb.plunge_down', 'plunge', 'down(?:wards?)?',
      'The temperature may plunge down tonight.',
      'The temperature may plunge tonight, and the road runs down the hill.')
    V('verb.plummet_down', 'plummet', 'down(?:wards?)?',
      'Share prices could plummet down on the news.',
      'Share prices could plummet on the news, and sales may go down.')
    V('verb.dwindle_down', 'dwindle', 'down',
      'The crowd began to dwindle down after the speech.',
      'The crowd began to dwindle after the speech, and the lights went down.')
    V('verb.skyrocket_up', 'skyrocket', 'up(?:wards?)?',
      'Prices skyrocket up whenever demand spikes.',
      'Prices skyrocket whenever demand spikes, and costs go up in winter.')
    V('verb.reduce_down', 'reduce', 'down',
      'We must reduce down the list to five names.',
      'We must reduce the list to five names, and then narrow it down by vote.')
    V('verb.separate_apart', 'separate', 'apart',
      'Separate apart the red and the white clothes.',
      'Separate the red and the white clothes, and set them apart for washing.')
    ids.append(add('verb.over_exaggerate',
                   rf'(?im){S}(?P<target>over[- ]?(?P<v>exaggerat(?:e|es|ed|ing|ion|ions))){E}', '${v}', 'Style', 0.78,
                   '“Over-exaggerate” says the same thing twice: “exaggerate” already means to go too far.',
                   'Do not over-exaggerate the risk.',
                   'Do not exaggerate the risk, and overlook nothing in the survey.'))
    ids.append(add('verb.exit_out',
                   rf'(?im){S}(?:to|will|would|can|could|should|must|may|might|shall|please|just|then|and|or|not|I|we|you|they|he|she|it|'
                   rf'don[’\']t|didn[’\']t|doesn[’\']t|let[’\']s|let us|never|always|also|first) (?P<target>(?P<v>exit(?:s|ed|ing)?) out(?: of)?){E}',
                   '${v}', 'Style', 0.78,
                   '“Exit out of” says the same thing twice: “exit” already means to go out.',
                   'Press the button to exit out of the app.',
                   'Press the button to exit the app. The exit out of the car park is on the left.'))
    ids.append(add('verb.visualize_in_mind',
                   rf'(?im){S}(?:visuali[sz]|imagin|envision)(?:e|es|ed|ing)(?: (?:it|this|that|them|these|those|the \w+|a \w+|your \w+))?'
                   rf'(?P<target> in (?:my|your|his|her|our|their) (?:mind|head))(?:[^\w\'’-]|$)',
                   '', 'Style', 0.76,
                   'To visualize or imagine is already to do it in the mind: drop “in your mind”.',
                   'Try to visualize the result in your mind.',
                   'Try to visualize the result. A picture of it hangs in the mind of every fan.'))
    for vb, pos in (('oscillat', 'The needle will oscillate back and forth.'),
                    ('vacillat', 'The committee tends to vacillate back and forth.'),
                    ('alternat', 'The lights alternate back and forth.')):
        ids.append(add(f'verb.{vb}e_back_and_forth',
                       rf'(?im){S}(?P<target>(?P<v>{vb}(?:e|es|ed|ing)) back and forth){E}', '${v}', 'Style', 0.76,
                       f'“{vb}e back and forth” says the same thing twice: “{vb}e” already means back and forth.',
                       pos, f'The needle will {vb}e. The ball rolled back and forth across the floor.'))
    ids.append(add('verb.from_whence',
                   rf'(?im){S}(?P<target>from whence){E}', 'whence', 'Style', 0.76,
                   '“Whence” already means “from where”: say “whence”, or “from where”.',
                   'They went back to the town from whence they came.',
                   'They went back to the town whence they came, and from there to the coast.'))
    return ids
