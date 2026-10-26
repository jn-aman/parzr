"""An adjective followed by the noun it already measures: "blue in color", "large in size", "round in shape"."""
from core import add, style, S, E

SEC = 'Adjective plus the dimension it names'


def dim(rid, adjs, noun, pos, neg, conf=0.72, nounre=None):
    nre = nounre or noun
    adj = '|'.join(adjs)
    reason = f'The adjective already tells the {noun}: “{adjs[0]} in {noun}” can be just “{adjs[0]}”.'
    return add(f'dim.{rid}', rf'(?im){S}(?P<target>(?P<a>{adj}) in {nre}){E}', '${a}', 'Style', conf, reason, pos, neg)


def build():
    ids = []
    d = lambda *a, **k: ids.append(dim(*a, **k))
    d('color', ['red', 'orange', 'yellow', 'green', 'blue', 'purple', 'violet', 'pink', 'brown', 'black', 'white', 'gray',
                'grey', 'golden', 'silver', 'beige', 'maroon', 'turquoise', 'crimson', 'scarlet'], 'color',
      'The new bike is bright blue in color.',
      'The new bike is bright blue, and the colors in the poster are warm.', nounre='colou?r')
    d('size', ['large', 'small', 'big', 'huge', 'tiny', 'enormous', 'massive', 'gigantic', 'bigger', 'larger', 'smaller',
               'biggest', 'largest', 'smallest', 'medium'], 'size',
      'The new phone is small in size.',
      'The new phone is small, and the differences in size are slight.')
    d('shape', ['round', 'square', 'oval', 'circular', 'rectangular', 'triangular', 'spherical', 'cylindrical', 'conical',
                'cubic', 'hexagonal', 'octagonal', 'pentagonal', 'oblong'], 'shape',
      'The table is oval in shape.',
      'The table is oval, and the changes in shape were small.')
    d('weight', ['heavy', 'light', 'heavier', 'lighter', 'heaviest', 'lightest'], 'weight',
      'The bag is light in weight.',
      'The bag is light, and the gain in weight was small.')
    d('height', ['tall', 'short', 'taller', 'shorter', 'tallest', 'shortest'], 'height',
      'The tower is tall in height.',
      'The tower is tall, and the rise in height is small.')
    d('length', ['long', 'short', 'longer', 'shorter', 'longest', 'shortest'], 'length',
      'The cable is long in length.',
      'The cable is long, and the change in length is small.')
    d('width', ['wide', 'narrow', 'wider', 'narrower', 'widest', 'narrowest'], 'width',
      'The gap is narrow in width.',
      'The gap is narrow, and the changes in width were small.')
    d('depth', ['deep', 'shallow', 'deeper', 'shallower', 'deepest', 'shallowest'], 'depth',
      'The pool is shallow in depth.',
      'The pool is shallow, and the change in depth was small.')
    d('age', ['old', 'young', 'older', 'younger', 'oldest', 'youngest'], 'age',
      'The tree is old in age.',
      'The tree is old, and the gap in age is large.')
    d('number', ['few', 'many', 'several', 'numerous', 'countless'], 'number',
      'The seats are few in number.',
      'The seats are few, and the rise in number was steady.')
    d('temperature', ['hot', 'cold', 'warm', 'cool', 'freezing', 'boiling', 'chilly'], 'temperature',
      'The water was cold in temperature.',
      'The water was cold, and the change in temperature was sudden.')
    d('price', ['expensive', 'cheap', 'costly', 'inexpensive', 'pricey', 'affordable'], 'price',
      'The coat is cheap in price.',
      'The coat is cheap, and the jump in price was sudden.')
    d('speed', ['fast', 'slow', 'quick', 'rapid', 'faster', 'slower'], 'speed',
      'The new train is fast in speed.',
      'The new train is fast, and the gain in speed is large.')
    d('volume', ['loud', 'quiet', 'soft', 'louder', 'quieter'], 'volume',
      'The alarm is loud in volume.',
      'The alarm is loud, and the drop in volume was slight.')
    d('taste', ['sweet', 'sour', 'bitter', 'salty', 'spicy', 'bland', 'sweeter', 'bitterer'], 'taste',
      'The soup was salty in taste.',
      'The soup was salty, and the shift in taste was slight.', nounre='tastes?')
    d('texture', ['soft', 'smooth', 'rough', 'coarse', 'hard', 'silky', 'gritty', 'softer', 'smoother', 'rougher'],
      'texture',
      'The cloth is smooth in texture.',
      'The cloth is smooth, and the change in texture is slight.')
    d('duration', ['short', 'brief', 'long', 'lengthy', 'extended'], 'duration',
      'The meeting was brief in duration.',
      'The meeting was brief, and the rise in duration was slight.')
    d('strength', ['strong', 'weak', 'stronger', 'weaker'], 'strength',
      'The rope is strong in strength.',
      'The rope is strong, and the gain in strength was clear.')
    return ids
