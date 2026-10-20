# passphrase, password, words, diceware, memorable, generator

from typing import Literal
import math
import secrets

WORDS = (
    "acid actor apple arrow atlas badge baker basin beach berry birch blade blank blaze bloom board bonus "
    "booth brave bread brick bride brook brush cabin cable camel candy canoe cargo carol cedar chain chalk "
    "charm chess chief child cider cigar civic claim clerk cliff clock cloud coach coast cobra comet coral "
    "couch craft crane crash cream crest crowd crown curve cycle daisy dance delta depot diary diner dodge "
    "donor dough draft dream dress drift drill drink drive eagle earth eight elbow elder ember empty enemy "
    "entry equal event fable fairy faith fancy feast fence ferry fever fiber field fifty flame flash fleet "
    "flint flour fluid focus forge frame frost fruit gamer giant ginger glade glass globe gloss glove grace "
    "grain grand grape grass gravy green grove guard guest guide guitar habit happy harbor hatch haven hazel "
    "heart hedge heron hobby honey horse hotel house human humor image index inner ivory jelly jewel joint "
    "judge juice jumbo karma kayak kiosk knife koala label lager lance latch laugh layer lemon level light "
    "lilac linen lion llama lodge logic lotus lucky lunar lunch magic major mango maple march medal melon "
    "mercy metal meter micro minor model money month moose motor mount mouse movie mural music nerve night "
    "noble north novel nurse oasis ocean olive onion opera orbit organ otter oxide paint panda paper party "
    "pasta patch peach pearl pedal penny petal piano pilot pixel pizza plaza plumb poem polar porch pound "
    "power prime prize proof pulse punch pupil quail quart queen quest quick quiet radar radio raven relay "
    "ridge river roast robot rocky rogue round royal ruler rumor saber salad salsa sandy satin sauce scale "
    "scene scoop scout seven shade shark sheep shelf shell shine shirt shore siren skate sleep slice smile "
    "snack solar solid sonic sound space spark spice spine spoon sport squid stack stage stamp steam steel "
    "stone storm story straw sugar sunny super surf swamp sweet sword table tango teach tempo tiger timer "
    "title toast token topaz torch total tower track trail train treat tribe trout truck trunk tulip tutor "
    "twist ultra uncle union unity urban valley value vapor vault velvet venus verse video villa vinyl violet "
    "visit vivid vocal voice wagon waltz water wheat whale wheel while whisk widow witch woman world worth "
    "yacht yield young zebra zesty"
).split()


def passphrase_generator(
    words: int = 5,
    separator: Literal["dash", "space", "dot", "underscore", "none"] = "dash",
    capitalise: Literal["no", "yes"] = "no",
    add_number: Literal["no", "yes"] = "no",
    count: int = 5,
) -> dict:
    """Memorable passphrases made of random dictionary words
    (correct-horse-battery-staple style) with the entropy in bits. Five words from
    this list is about 43 bits; six is 51.
    """
    words = max(3, min(words, 10))
    sep = {"dash": "-", "space": " ", "dot": ".", "underscore": "_", "none": ""}[separator]
    phrases = []
    for _ in range(max(1, min(count, 50))):
        chosen = [secrets.choice(WORDS) for _ in range(words)]
        if capitalise == "yes":
            chosen = [w.capitalize() for w in chosen]
        phrase = sep.join(chosen)
        if add_number == "yes":
            phrase += sep + str(secrets.randbelow(100))
        phrases.append(phrase)
    entropy = words * math.log2(len(WORDS)) + (math.log2(100) if add_number == "yes" else 0)
    return {"passphrases": phrases, "entropy_bits": round(entropy, 1), "word_list_size": len(WORDS)}
