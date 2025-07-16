from json import load
from pathlib import Path

ROOT = Path(__file__).parent.parent

with open(ROOT / 'static/cities.json') as file:
    CITIES = load(file)

with open(ROOT / 'static/countries.json') as file:
    COUNTRIES = load(file)

MIN_YEAR, MAX_YEAR = 1918, 2018

LINKS = {
    'dribbble': '<a href="https://dribbble.com/{0}">Dribbble</a>',
    'github': '<a href="https://github.com/{0}">GitHub</a>',
    'instagram': '<a href="https://instagram.com/{0}">Instagram</a>',
    'linkedin': '<a href="https://linkedin.com/in/{0}">LinkedIn</a>',
    'patreon': '<a href="https://patreon.com/{0}">Patreon</a>',
    'paypal': '<a href="https://paypal.me/{0}">PayPal</a>',
    'pinboard': '<a href="https://pinboard.in/u:{0}/">Pinboard</a>',
    'reddit': '<a href="https://reddit.com/u/{0}">Reddit</a>',
    'soundcloud': '<a href="https://soundcloud.com/{0}">SoundCloud</a>',
    'spotify': '<a href="https://open.spotify.com/user/{0}">Spotify</a>',
    'telegram': '<a href="https://t.me/{0}">Telegram</a>',
    'telephone': '<a href="tel:{0}">Telephone</a>',
    'twitter': '<a href="https://twitter.com/{0}">Twitter</a>',
    'x': '<a href="https://x.com/{0}">X</a>',
    'youtube': '<a href="https://youtube.com/@{0}">YouTube</a>'
}

LATIN = "-"
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
