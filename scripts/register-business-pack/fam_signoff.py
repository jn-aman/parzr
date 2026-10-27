"""Greetings and sign-offs: the comma conventions and the misspelled closings the spell checker misses."""
from core import rule

S = "Style"
NAME = r"(?-i:[A-Z][a-z.'’-]+)(?:[ \t]+(?-i:[A-Z][a-z.'’-]+)){0,2}"
def build():
    rule("signoff.regards_comma",
         rf"(?im)^(?P<target>(?:(?:best|kind|warm|many|with)\s+)?regards|(?:best|warm|kind) wishes|(?:thanks|thank you)\s+(?:and|&)\s+(?:(?:best|kind|warm)\s+)?regards)[ \t]*\r?\n[ \t]*{NAME}[ \t]*(?:\r?\n|$)",
         "${target},", S, 0.8,
         "A closing such as “Best regards” takes a comma before the name.",
         "Thanks for the update.\nBest regards\nAman Jain",
         "Thanks for the update.\nBest regards,\nAman Jain",
         "Thanks for the update.\nBest regards,\nAman Jain", "signoff")
    rule("signoff.closing_comma",
         rf"(?im)(?:\A|[.!?)”\"]\s*\n[ \t]*|\n[ \t]*\n[ \t]*)(?P<target>thanks|thank you|many thanks|thanks again|cheers|best|sincerely|sincerely yours|yours sincerely|yours faithfully|yours truly|respectfully|cordially)[ \t]*\r?\n[ \t]*{NAME}[ \t]*(?:\r?\n|$)",
         "${target},", S, 0.74,
         "A closing such as “Thanks” takes a comma before the name.",
         "I will send the file today.\nThanks\nAman",
         "I will send the file today.\nThanks,\nAman\nThanks for the quick reply\nI will send it today.",
         "I will send the file today.\nThanks,\nAman", "signoff")
    rule("signoff.regards_name_same_line",
         rf"(?im)^(?P<target>(?:(?:best|kind|warm|many|with)\s+)?regards)[ \t]+{NAME}[ \t]*$",
         "${target},", S, 0.8,
         "Put a comma after the closing: “Kind regards, Aman”.",
         "Kind regards Aman Jain",
         "Kind regards, Aman Jain\nRegards the matter, we cannot proceed.",
         "Kind regards, Aman Jain", "signoff")
    rule("signoff.dear_comma",
         rf"(?im)^dear\s+(?:(?:mr|mrs|ms|miss|dr|prof)\.?\s+)?(?:(?-i:[A-Z][a-z'’-]+)\s+){{0,2}}(?:sir or madam|madam or sir|(?-i:[A-Z][a-z'’-]+))(?P<target>)[ \t]*\r?\n[ \t]*\S",
         ",", S, 0.8,
         "A salutation takes a comma (or a colon) after the name.",
         "Dear Mr Patel\nI am writing about the invoice.",
         "Dear Mr Patel,\nI am writing about the invoice.\nDear Mr Patel:\nPlease see below.",
         "Dear Mr Patel,\nI am writing about the invoice.", "signoff")
    rule("signoff.hi_comma_name",
         rf"(?im)^(?:hi|hello|hey)(?P<target>,)[ \t]+{NAME},[ \t]*(?:\r?\n|$)",
         "", S, 0.66,
         "In a greeting the comma goes after the name: “Hi Aman,”.",
         "Hi, Aman,\nThe file is ready.",
         "Hi Aman,\nThe file is ready.\nHi, Mom! How was school?",
         "Hi Aman,\nThe file is ready.", "signoff")
    rule("signoff.regards_misspelled",
         r"(?im)^(?:(?:best|kind|warm|many|with|thanks (?:and|&))\s+)?(?P<target>regads|regardz|regrds|regrads|rgards|regars)\b",
         "regards", "Spelling", 0.92,
         "“Regards” is misspelled here.",
         "Thanks for the update.\nWarm regardz,\nAman",
         "Thanks for the update.\nWarm regards,\nAman",
         "Thanks for the update.\nWarm regards,\nAman", "signoff")
    rule("signoff.regard_singular",
         r"(?im)^(?:(?:best|kind|warm|many|with|thanks (?:and|&))\s+)(?P<target>regard)[ \t]*(?:[,.]|\r?\n|$)",
         "regards", "Word choice", 0.9,
         "A closing is “regards”, in the plural.",
         "Thanks for the update.\nKind regard,\nAman",
         "Thanks for the update.\nKind regards,\nAman",
         "Thanks for the update.\nKind regards,\nAman", "signoff")
    rule("signoff.wishes_misspelled",
         r"(?im)^(?:best|warm|kind|good|with)\s+(?P<target>wishs|wishis|wihses|wishees)\b",
         "wishes", "Spelling", 0.92,
         "“Wishes” is misspelled here.",
         "Thanks for the update.\nKind wishs,\nAman",
         "Thanks for the update.\nKind wishes,\nAman",
         "Thanks for the update.\nKind wishes,\nAman", "signoff")
