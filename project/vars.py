from datetime import date
from json import load
from pathlib import Path

ROOT = Path(__file__).parent.parent

with open(ROOT / 'static/cities.json') as file:
    CITIES = {k: set(v) for k, v in load(file).items()}

with open(ROOT / 'static/countries.json') as file:
    COUNTRIES = load(file)

MIN_AGE = 16
MAX_AGE = 99
COSTS = (8 * 12 + 20 * 2) * (date.today().year - 2014)

TYPES = [
    "work", "education", "project", "license", "certification",
    "course", "publication", "award", "cause", "volunteer"
]

NETWORKS = {
    'behance': ('Bēhance', 'https://behance.net/{0}'),
    'dribbble': ('Dribbble', 'https://dribbble.com/{0}'),
    'figma': ('Figma', 'https://figma.com/@{0}'),
    'github': ('GitHub', 'https://github.com/{0}'),
    'instagram': ('Instagram', 'https://instagram.com/{0}'),
    'linkedin': ('LinkedIn', 'https://linkedin.com/in/{0}'),
    'patreon': ('Patreon', 'https://patreon.com/{0}'),
    'paypal': ('PayPal', 'https://paypal.me/{0}'),
    'phone': ('Phone', 'tel:{0}'),
    'pinboard': ('Pinboard', 'https://pinboard.in/u:{0}/'),
    'pinterest': ('Pinterest', 'https://pinterest.com/{0}'),
    'reddit': ('Reddit', 'https://reddit.com/u/{0}'),
    'soundcloud': ('SoundCloud', 'https://soundcloud.com/{0}'),
    'spotify': ('Spotify', 'https://open.spotify.com/user/{0}'),
    'telegram': ('Telegram', 'https://t.me/{0}'),
    'threads': ('Threads', 'https://threads.com/@{0}'),
    'x': ('X', 'https://x.com/{0}'),
    'youtube': ('YouTube', 'https://youtube.com/@{0}'),
}

RESERVED = [
    "lm",
    "lucian",
    "lucianmarin",
    "sublevel"
]

INVALID = set(RESERVED + [
    "about",
    "account",
    "api",
    "arrivals",
    "at",
    "channel",
    "channels",
    "chat",
    "delete",
    "discover",
    "edit",
    "emoji",
    "feed",
    "followers",
    "following",
    "group",
    "groups",
    "invite",
    "invites",
    "login",
    "logout",
    "media",
    "member",
    "members",
    "mention",
    "mentions",
    "message",
    "messages",
    "news",
    "options",
    "password",
    "people",
    "policy",
    "privacy",
    "profile",
    "read",
    "recover",
    "replies",
    "reply",
    "request",
    "reset",
    "safety",
    "save",
    "saved",
    "saves",
    "search",
    "settings",
    "social",
    "static",
    "terms",
    "threads",
    "trending",
    "work",
    "xhr"
])


LATIN = ". "
LATIN += "abcdefghijklmnopqrstuvwxyz"
LATIN += "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
# lat-1
LATIN += "ÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏ"
LATIN += "ÐÑÒÓÔÕÖØÙÚÛÜÝÞß"
LATIN += "àáâãäåæçèéêëìíîï"
LATIN += "ðñòóôõöøùúûüýþÿ"
# ext-a
LATIN += "ĀāĂăĄąĆćĈĉĊċČčĎď"
LATIN += "ĐđĒēĔĕĖėĘęĚěĜĝĞğ"
LATIN += "ĠġĢģĤĥĦħĨĩĪīĬĭĮį"
LATIN += "İıĲĳĴĵĶķĸĹĺĻļĽľĿ"
LATIN += "ŀŁłŃńŅņŇňŉŊŋŌōŎŏ"
LATIN += "ŐőŒœŔŕŖŗŘřŚśŜŝŞş"
LATIN += "ŠšŢţŤťŦŧŨũŪūŬŭŮů"
LATIN += "ŰűŲųŴŵŶŷŸŹźŻżŽžſ"
# ext-b
LATIN += "ƀƁƂƃƄƅƆƇƈƉƊƋƌƍƎƏ"
LATIN += "ƐƑƒƓƔƕƖƗƘƙƚƛƜƝƞƟ"
LATIN += "ƠơƢƣƤƥƦƧƨƩƪƫƬƭƮƯ"
LATIN += "ưƱƲƳƴƵƶƷƸƹƺƻƼƽƾƿ"
LATIN += "ǀǁǂǃǄǅǆǇǈǉǊǋǌǍǎǏ"
LATIN += "ǐǑǒǓǔǕǖǗǘǙǚǛǜǝǞǟ"
LATIN += "ǠǡǢǣǤǥǦǧǨǩǪǫǬǭǮǯ"
LATIN += "ǰǱǲǳǴǵǶǷǸǹǺǻǼǽǾǿ"
LATIN += "ȀȁȂȃȄȅȆȇȈȉȊȋȌȍȎȏ"
LATIN += "ȐȑȒȓȔȕȖȗȘșȚțȜȝȞȟ"
LATIN += "ȠȡȢȣȤȥȦȧȨȩȪȫȬȭȮȯ"
LATIN += "ȰȱȲȳȴȵȶȷȸȹȺȻȼȽȾȿ"
LATIN += "ɀɁɂɃɄɅɆɇɈɉɊɋɌɍɎɏ"
LATIN = set(LATIN)
