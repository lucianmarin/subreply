from json import load
from pathlib import Path


with open(Path(__file__).parent.parent / 'static/worldcities.json') as file:
    WORLD = load(file)

MIN_YEAR, MAX_YEAR = 1918, 2018

SOCIAL = {
    'dribbble': '<a href="https://dribbble.com/{0}">Dribbble</a>',
    'github': '<a href="https://github.com/{0}">GitHub</a>',
    'instagram': '<a href="https://instagram.com/{0}">Instagram</a>',
    'linkedin': '<a href="https://linkedin.com/in/{0}">LinkedIn</a>',
    'patreon': '<a href="https://patreon.com/{0}">Patreon</a>',
    'paypal': '<a href="https://paypal.me/{0}">PayPal</a>',
    'soundcloud': '<a href="https://soundcloud.com/{0}">SoundCloud</a>',
    'spotify': '<a href="https://open.spotify.com/user/{0}">Spotify</a>',
    'telegram': '<a href="https://t.me/{0}">Telegram</a>',
    'twitter': '<a href="https://twitter.com/{0}">Twitter</a>'
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

ACTIVITY_HTML = (
    "<html>"
    "<p>Hello,</p>"
    "<p>You got a couple of {{ notifs }} left unseen on your Subreply account.</p>"
    "<p>Login from https://subreply.com/login to check them out. Your username is @{{ username }}.</p>"
    "<p>You won't be emailed again in couple of months if there's no activity on your account.</p>"
    "<p>Have a sunny day!</p>"
    "</html>"
)

ACTIVITY_TEXT = (
    "Hello,\n"
    "You got a couple of {{ notifs }} left unseen on your Subreply account.\n"
    "Login from https://subreply.com/login to check them out. Your username is @{{ username }}.\n"
    "You won't be emailed again in couple of months if there's no activity on your account.\n"
    "Have a sunny day!\n"
)

UNLOCK_HTML = (
    "<html>"
    "<p>Hello,</p>"
    "<p>Unlock your account on Subreply by going to https://subreply.com/unlock/{{ token }}</p>"
    "<p>Your username is @{{ username }}.</p>"
    "<p>Delete this email if you didn't make such request.</p>"
    "</html>"
)

UNLOCK_TEXT = (
    "Hello,\n"
    "Unlock your account on Subreply by going to https://subreply.com/unlock/{{ token }}\n"
    "Your username is @{{ username }}.\n"
    "Delete this email if you didn't make such request.\n"
)

HEADERS = {
    'User-Agent': "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/12.0 Safari/605.1.15",
    'Accept': "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
}

FEEDS = [
    # "http://feeds.arstechnica.com/arstechnica/index",
    # "http://feeds.arstechnica.com/arstechnica/features",
    "http://rss.sciam.com/scientificamerican-global",
    # "http://feeds.reuters.com/news/artsculture",
    # "http://feeds.reuters.com/reuters/businessNews",
    # "http://feeds.reuters.com/reuters/entertainment",
    # "http://feeds.reuters.com/reuters/environment",
    # "http://feeds.reuters.com/reuters/healthNews",
    # "http://feeds.reuters.com/reuters/oddlyEnoughNews",
    # "http://feeds.reuters.com/reuters/scienceNews",
    # "http://feeds.reuters.com/reuters/technologyNews",
    "http://feeds.hbr.org/harvardbusiness/",
    "http://feeds.macrumors.com/macrumors-front",
    "http://feeds.crackberry.com/crackberry/qbtb",
    "http://feeds.imore.com/theiphoneblog",
    "http://feeds.androidcentral.com/androidcentral",
    "http://feeds.windowscentral.com/wmexperts",
    # "http://feeds.feedburner.com/businessinsider",
    "http://feeds.feedburner.com/fubiz",
    "http://feeds.feedburner.com/neowin-main",
    "http://feeds.feedburner.com/petapixel",
    "http://feeds.feedburner.com/thehackersnews",
    "http://feeds.feedburner.com/venturebeat/szyf",
    "http://feeds.feedburner.com/sub/9to5google",
    "http://feeds.feedburner.com/sub/9to5mac",
    "http://feeds.feedburner.com/sub/aeon",
    "http://feeds.feedburner.com/sub/aestheticamagazine",
    "http://feeds.feedburner.com/sub/anandtech",
    "http://feeds.feedburner.com/sub/arenaev",
    "http://feeds.feedburner.com/sub/atlantic",
    "http://feeds.feedburner.com/sub/axios",
    # "http://feeds.feedburner.com/sub/balkaninsight",
    "http://feeds.feedburner.com/sub/berkeley",
    "http://feeds.feedburner.com/sub/bgr",
    "http://feeds.feedburner.com/sub/comingsoon",
    "http://feeds.feedburner.com/sub/conversation",
    "http://feeds.feedburner.com/sub/dailyartmag",
    "http://feeds.feedburner.com/sub/deepmind",
    "http://feeds.feedburner.com/sub/distill",
    "http://feeds.feedburner.com/sub/eff",
    "http://feeds.feedburner.com/sub/electrek",
    "http://feeds.feedburner.com/sub/endpoints",
    # "http://feeds.feedburner.com/sub/engadget",
    "http://feeds.feedburner.com/sub/fastcompany",
    "http://feeds.feedburner.com/sub/fs",
    "http://feeds.feedburner.com/sub/fubiz",
    "http://feeds.feedburner.com/sub/gsmarena",
    "http://feeds.feedburner.com/sub/karpathy",
    "http://feeds.feedburner.com/sub/kottke",
    "http://feeds.feedburner.com/sub/japantimes",
    "http://feeds.feedburner.com/sub/joshmitteldorf",
    "http://feeds.feedburner.com/sub/increment",
    "http://feeds.feedburner.com/sub/infoq",
    "http://feeds.feedburner.com/sub/lifeextension",
    "http://feeds.feedburner.com/sub/lifespan",
    "http://feeds.feedburner.com/sub/longreads",
    "http://feeds.feedburner.com/sub/massivesci",
    "http://feeds.feedburner.com/sub/mit",
    "http://feeds.feedburner.com/sub/mspoweruser",
    "http://feeds.feedburner.com/sub/nautilus",
    # "http://feeds.feedburner.com/sub/npr",
    "http://feeds.feedburner.com/sub/nytimes/science",
    "http://feeds.feedburner.com/sub/nytimes/tech",
    "http://feeds.feedburner.com/sub/omgubuntu",
    "http://feeds.feedburner.com/sub/peterattia",
    "http://feeds.feedburner.com/sub/polygon",
    "http://feeds.feedburner.com/sub/producthunt",
    "http://feeds.feedburner.com/sub/quantamagazine",
    "http://feeds.feedburner.com/sub/quillette",
    "http://feeds.feedburner.com/sub/qz",
    # "http://feeds.feedburner.com/sub/register",
    "http://feeds.feedburner.com/sub/semiaccurate",
    "http://feeds.feedburner.com/sub/seth",
    "http://feeds.feedburner.com/sub/sixthtone",
    "http://feeds.feedburner.com/sub/smashing",
    # "http://feeds.feedburner.com/sub/techcrunch",
    "http://feeds.feedburner.com/sub/spacenews",
    "http://feeds.feedburner.com/sub/thefreethoughtproject",
    "http://feeds.feedburner.com/sub/thegradient",
    "http://feeds.feedburner.com/sub/tidbits",
    "http://feeds.feedburner.com/sub/verge",
    "http://feeds.feedburner.com/sub/vice",
    "http://feeds.feedburner.com/sub/vox",
    "http://feeds.feedburner.com/sub/wired",
    "http://feeds.feedburner.com/sub/windowslatest"
]

INVALID = [
    "about",
    "account",
    "api",
    "delete",
    "discover",
    "edit",
    "emoji",
    "feed",
    "followers",
    "following",
    "invites",
    "lm",
    "lobby",
    "login",
    "logout",
    "luc",
    "lucianmarin",
    "media",
    "mention",
    "mentioned",
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
    "re",
    "read",
    "reply",
    "replying",
    "request",
    "reset",
    "save",
    "saved",
    "saves",
    "search",
    "settings",
    "social",
    "static",
    "sub",
    "sublevel",
    "terms",
    "trending",
    "unlock"
]
