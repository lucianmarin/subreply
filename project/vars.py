from json import load
from pathlib import Path

ROOT = Path(__file__).parent.parent

with open(ROOT / 'static/cities.json') as file:
    CITIES = load(file)

with open(ROOT / 'static/countries.json') as file:
    COUNTRIES = load(file)

MIN_AGE = 16
MAX_AGE = 100

TYPES = [
    "work", "education", "project", "license", "certification",
    "course", "publication", "award", "cause", "volunteer"
]

LINKS = {
    'dribbble': '<a href="https://dribbble.com/{0}" rel="me">Dribbble</a>',
    'github': '<a href="https://github.com/{0}" rel="me">GitHub</a>',
    'instagram': '<a href="https://instagram.com/{0}" rel="me">Instagram</a>',
    'linkedin': '<a href="https://linkedin.com/in/{0}" rel="me">LinkedIn</a>',
    'patreon': '<a href="https://patreon.com/{0}" rel="me">Patreon</a>',
    'paypal': '<a href="https://paypal.me/{0}" rel="me">PayPal</a>',
    'pinboard': '<a href="https://pinboard.in/u:{0}/" rel="me">Pinboard</a>',
    'reddit': '<a href="https://reddit.com/u/{0}" rel="me">Reddit</a>',
    'soundcloud': '<a href="https://soundcloud.com/{0}" rel="me">SoundCloud</a>',
    'spotify': '<a href="https://open.spotify.com/user/{0}" rel="me">Spotify</a>',
    'telegram': '<a href="https://t.me/{0}" rel="me">Telegram</a>',
    'telephone': '<a href="tel:{0}" rel="me">Telephone</a>',
    'twitter': '<a href="https://twitter.com/{0}" rel="me">Twitter</a>',
    'x': '<a href="https://x.com/{0}" rel="me">X</a>',
    'youtube': '<a href="https://youtube.com/@{0}" rel="me">YouTube</a>'
}

RESERVED = [
    "lm",
    "lucian",
    "lucianmarin",
    "sublevel"
]

INVALID = RESERVED + [
    "about",
    "account",
    "api",
    "arrivals",
    "at",
    "channel",
    "channels",
    "chat",
    "delete",
    "details",
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
    "xhr"
]


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
