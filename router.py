from falcon import App
from falcon.constants import MEDIA_HTML

from app import resources, xhr
from project.settings import DEBUG

app = App(media_type=MEDIA_HTML)

app.req_options.strip_url_path_trailing_slash = True

app.resp_options.secure_cookies_by_default = not DEBUG

app.add_route('/', resources.MainResource())

app.add_route('/xhr/unsend/{id:int}', xhr.TextCallback(), suffix="unsend")
app.add_route('/xhr/delete/{id:int}', xhr.PostCallback(), suffix="delete")
app.add_route('/xhr/save/{id:int}', xhr.PostCallback(), suffix="save")
app.add_route('/xhr/unsave/{id:int}', xhr.PostCallback(), suffix="unsave")
app.add_route('/xhr/follow/{username}', xhr.BondCallback(), suffix="follow")
app.add_route('/xhr/unfollow/{username}', xhr.BondCallback(), suffix="unfollow")

app.add_route('/feed', resources.FeedResource())
app.add_route('/following', resources.FollowingResource())
app.add_route('/followers', resources.FollowersResource())
app.add_route('/mentions', resources.MentionsResource())
app.add_route('/messages', resources.InboxResource())
app.add_route('/replies', resources.RepliesResource())
app.add_route('/saved', resources.SavedResource())

# app.add_route('/links', resources.LinksResource())
app.add_route('/people', resources.PeopleResource())
app.add_route('/trending', resources.TrendingResource())
app.add_route('/discover', resources.DiscoverResource())

app.add_route('/about', resources.AboutResource())
app.add_route('/terms', resources.AboutResource(), suffix="terms")
app.add_route('/privacy', resources.AboutResource(), suffix="privacy")
app.add_route('/emoji', resources.EmojiResource())

app.add_route('/robots.txt', resources.TxtResource(), suffix="bots")
app.add_route('/sitemap.txt', resources.TxtResource(), suffix="map")

app.add_route('/login', resources.LoginResource())
app.add_route('/logout', resources.LogoutResource())
app.add_route('/register', resources.RegisterResource())
app.add_route('/recover', resources.RecoverResource())
app.add_route('/recover/{token}', resources.RecoverResource(), suffix="link")

app.add_route('/account', resources.AccountResource())
app.add_route('/account/change', resources.AccountResource(), suffix="change")
app.add_route('/account/delete', resources.AccountResource(), suffix="delete")
app.add_route('/account/export', resources.AccountResource(), suffix="export")

app.add_route('/profile', resources.ProfileResource())
app.add_route('/details', resources.DetailsResource())

app.add_route('/arrivals', resources.ArrivalsResource())
app.add_route('/arrivals/destroy', resources.ArrivalsResource(), suffix="destroy")

app.add_route('/reply/{id:int}', resources.ReplyResource())
app.add_route('/edit/{id:int}', resources.EditResource())
app.add_route('/message/{username}', resources.MessageResource())
app.add_route('/{username}/approve', resources.ArrivalsResource(), suffix="approve")
app.add_route('/{username}', resources.MemberResource())

if DEBUG:
    app.add_route('/static/{filename}', resources.StaticResource())
    app.add_route('/static/route159/{filename}', resources.StaticResource("route159"))

application = app
