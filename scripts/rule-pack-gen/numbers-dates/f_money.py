"""Currency: symbol plus the currency word, "5 dollar", "1 dollars", "$ 5"."""
from lib import add, CARD2U, TAIL

LEAD = r'(?:^|[^/\s]\s+|\()'   # a number is not read after a slash ("1 / 2 second", "5 / 4 time")
AMT = r'\d[\d,]*(?:\.\d+)?'
SCALE = r'(?: (?:thousand|million|billion|trillion|lakh|lakhs|crore|crores|k|m|bn))?'

add('money.dollar_sign_and_word', r'(?i)\$' + AMT + SCALE + r'(?P<target> dollars)\b', '', 'Redundancy', 0.8,
    'The “$” sign already says dollars: write “$5” or “5 dollars”, not both.',
    'The ticket costs $5 dollars.', 'The ticket costs $5, or 5 dollars, or $5 million.',
    'The ticket costs $5.')
add('money.pound_sign_and_word', r'(?i)£' + AMT + SCALE + r'(?P<target> pounds)\b', '', 'Redundancy', 0.8,
    'The “£” sign already says pounds: write “£5” or “5 pounds”, not both.',
    'The ticket costs £5 pounds.', 'The ticket costs £5, or 5 pounds, or £5 million.',
    'The ticket costs £5.')
add('money.euro_sign_and_word', r'(?i)€' + AMT + SCALE + r'(?P<target> euros?)\b', '', 'Redundancy', 0.8,
    'The “€” sign already says euros: write “€5” or “5 euros”, not both.',
    'The ticket costs €5 euros.', 'The ticket costs €5, or 5 euros, or €5 million.',
    'The ticket costs €5.')
add('money.rupee_sign_and_word', r'(?i)(?:₹|\bRs\.?|\bINR) ?' + AMT + SCALE + r'(?P<target> rupees)\b', '', 'Redundancy', 0.8,
    'The sign “₹” or “Rs” already says rupees: write “Rs 500” or “500 rupees”, not both.',
    'The fee is Rs. 500 rupees per head.', 'The fee is Rs. 500 per head, or 500 rupees, or ₹500.',
    'The fee is Rs. 500 per head.')
add('money.yen_sign_and_word', r'(?i)¥' + AMT + SCALE + r'(?P<target> yen)\b', '', 'Redundancy', 0.8,
    'The “¥” sign already says yen: write “¥500” or “500 yen”, not both.',
    'The snack costs ¥500 yen at the shop.', 'The snack costs ¥500 at the shop, or 500 yen.',
    'The snack costs ¥500 at the shop.')
add('money.plural_after_number',
    r'(?i)' + LEAD + CARD2U + r' (?P<target>(?P<u>(?-i:dollar|rupee|cent|dirham|rouble|ruble|dinar)))' + TAIL,
    '${u}s', 'Grammar', 0.9,
    'After a number above one the currency word is plural: “5 dollars”, “10 cents”.',
    'The bag costs 5 dollar in total.', 'The bag costs 5 dollars in total, and a 5 dollar bag sells out.',
    'The bag costs 5 dollars in total.')
add('money.singular_after_one',
    r'(?i)' + LEAD + r'1 (?P<target>(?P<u>(?-i:dollar|rupee|cent|euro|pound|dirham|rouble|ruble|dinar))s)\b',
    '${u}', 'Grammar', 0.9,
    'Exactly 1 takes the singular: “1 dollar”, “1 cent”.',
    'The bag costs 1 dollars today.', 'The bag costs 1 dollar today, or 1.5 dollars, or 0.1 pounds.',
    'The bag costs 1 dollar today.')
add('money.one_lakh_plural', r'(?i)' + LEAD + r'1 (?P<target>(?P<u>(?-i:lakh|crore))s)\b', '${u}', 'Grammar', 0.88,
    'Exactly 1 takes the singular: “1 lakh”, “1 crore”.',
    'The loan was 1 lakhs in total.', 'The loan was 1 lakh in total, or 10 lakhs, or 2 crores.',
    'The loan was 1 lakh in total.')
