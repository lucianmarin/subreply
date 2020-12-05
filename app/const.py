import json

with open('static/worldcities.json') as file:
    WORLD = json.load(file)

MIN_YEAR, MAX_YEAR = 1918, 2018

LATIN = "abcdefghijklmnopqrstuvwxyz"
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

HTML = "<html><p>Hello,</p><p>You can change your password for @{{ username }} on Subreply using the following link https://subreply.com/reset/{{ code }} and after that you will be logged in with the new credentials.</p><p>Delete this email if you didn't make such request.</p>"

TEXT = "Hello,\nYou can change your password for @{{ username }} on Subreply using the following link https://subreply.com/reset/{{ code }} and after that you will be logged in with the new credentials.\nDelete this email if you didn't make such request."
