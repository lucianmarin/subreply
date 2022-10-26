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

EMOJIS = {
    "japantimes.co.jp": ":Japan:",
    "gsmarena.com": ":mobile_phone:",
    "comingsoon.net": ":popcorn:",
    "arenaev.com": ":sport_utility_vehicle:",
    "polygon.com": ":joystick:",
    "electrek.co": ":sport_utility_vehicle:",
    "dailyartmagazine.com": ":framed_picture:",
    "petapixel.com": ":camera:",
    "spacenews.com": ":ringed_planet:"
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
    # "https://feeds.feedburner.com/businessinsider",
    "https://feeds.feedburner.com/fubiz",
    "https://feeds.feedburner.com/neowin-main",
    "https://feeds.feedburner.com/petapixel",
    "https://feeds.feedburner.com/thehackersnews",
    "https://feeds.feedburner.com/venturebeat/szyf",
    "https://feeds.feedburner.com/sub/9to5google",
    "https://feeds.feedburner.com/sub/9to5mac",
    "https://feeds.feedburner.com/sub/aeon",
    "https://feeds.feedburner.com/sub/aestheticamagazine",
    "https://feeds.feedburner.com/sub/anandtech",
    "https://feeds.feedburner.com/sub/arenaev",
    "https://feeds.feedburner.com/sub/atlantic",
    "https://feeds.feedburner.com/sub/atlasobscura",
    "https://feeds.feedburner.com/sub/axios",
    # "https://feeds.feedburner.com/sub/balkaninsight",
    "https://feeds.feedburner.com/sub/berkeley",
    "https://feeds.feedburner.com/sub/bgr",
    "https://feeds.feedburner.com/sub/comingsoon",
    "https://feeds.feedburner.com/sub/conversation",
    "https://feeds.feedburner.com/sub/dailyartmag",
    "https://feeds.feedburner.com/sub/deepmind",
    "https://feeds.feedburner.com/sub/distill",
    "https://feeds.feedburner.com/sub/eff",
    "https://feeds.feedburner.com/sub/electrek",
    "https://feeds.feedburner.com/sub/endpoints",
    # "https://feeds.feedburner.com/sub/engadget",
    "https://feeds.feedburner.com/sub/fastcompany",
    "https://feeds.feedburner.com/sub/fs",
    "https://feeds.feedburner.com/sub/fubiz",
    "https://feeds.feedburner.com/sub/gsmarena",
    "https://feeds.feedburner.com/sub/karpathy",
    "https://feeds.feedburner.com/sub/kottke",
    "https://feeds.feedburner.com/sub/japantimes",
    "https://feeds.feedburner.com/sub/joshmitteldorf",
    "https://feeds.feedburner.com/sub/increment",
    "https://feeds.feedburner.com/sub/infoq",
    "https://feeds.feedburner.com/sub/lesswrong",
    "https://feeds.feedburner.com/sub/lifeextension",
    "https://feeds.feedburner.com/sub/lifespan",
    "https://feeds.feedburner.com/sub/longreads",
    "https://feeds.feedburner.com/sub/massivesci",
    "https://feeds.feedburner.com/sub/mit",
    "https://feeds.feedburner.com/sub/mspoweruser",
    "https://feeds.feedburner.com/sub/nautilus",
    # "https://feeds.feedburner.com/sub/npr",
    "https://feeds.feedburner.com/sub/nytimes/science",
    "https://feeds.feedburner.com/sub/nytimes/tech",
    "https://feeds.feedburner.com/sub/omgubuntu",
    "https://feeds.feedburner.com/sub/peterattia",
    "https://feeds.feedburner.com/sub/polygon",
    "https://feeds.feedburner.com/sub/producthunt",
    "https://feeds.feedburner.com/sub/quantamagazine",
    "https://feeds.feedburner.com/sub/quillette",
    "https://feeds.feedburner.com/sub/qz",
    # "https://feeds.feedburner.com/sub/register",
    "https://feeds.feedburner.com/sub/sciencenews",
    "https://feeds.feedburner.com/sub/semiaccurate",
    "https://feeds.feedburner.com/sub/seth",
    "https://feeds.feedburner.com/sub/singularityhub",
    "https://feeds.feedburner.com/sub/sixthtone",
    "https://feeds.feedburner.com/sub/smashing",
    "https://feeds.feedburner.com/sub/smithsonianmag",
    # "https://feeds.feedburner.com/sub/techcrunch",
    "https://feeds.feedburner.com/sub/spacenews",
    "https://feeds.feedburner.com/sub/thefreethoughtproject",
    "https://feeds.feedburner.com/sub/thegradient",
    "https://feeds.feedburner.com/sub/tidbits",
    "https://feeds.feedburner.com/sub/verge",
    "https://feeds.feedburner.com/sub/vice",
    "https://feeds.feedburner.com/sub/vox",
    "https://feeds.feedburner.com/sub/wired",
    "https://feeds.feedburner.com/sub/windowslatest"
]
