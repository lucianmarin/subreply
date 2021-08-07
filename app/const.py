import json

with open('static/worldcities.json') as file:
    WORLD = json.load(file)

MIN_YEAR, MAX_YEAR = 1918, 2018

SITES = {
    'dribbble': '<a href="https://dribbble.com/{0}">Dribbble</a>',
    'github': '<a href="https://github.com/{0}">GitHub</a>',
    'instagram': '<a href="https://instagram.com/{0}">Instagram</a>',
    'linkedin': '<a href="https://linkedin.com/in/{0}">LinkedIn</a>',
    'pinterest': '<a href="https://pinterest.com/{0}">Pinterest</a>',
    'soundcloud': '<a href="https://soundcloud.com/{0}">SoundCloud</a>',
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

HTML = (
    "<html>"
    "<p>Hello,</p>"
    "<p>Unlock your account on Subreply by going to https://subreply.com/unlock/{{ token }}</p>"
    "<p>Your username is: {{ username }}</p>"
    "<p>Delete this email if you didn't make such request.</p>"
    "</html>"
)

TEXT = (
    "Hello,\n"
    "Unlock your account on Subreply by going to https://subreply.com/unlock/{{ token }}\n"
    "Your username is: {{ username }}\n"
    "Delete this email if you didn't make such request.\n"
)
