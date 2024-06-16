from falcon import App
from falcon.constants import MEDIA_HTML

from app import api, resources
from project.settings import DEBUG

app = App(media_type=MEDIA_HTML)

app.req_options.auto_parse_form_urlencoded = True
app.req_options.strip_url_path_trailing_slash = True

app.resp_options.secure_cookies_by_default = not DEBUG

app.add_route('/', resources.MainResource())

app.add_route('/api/delete/{id:int}', api.DeleteEndpoint())
app.add_route('/api/save/{id:int}', api.SaveEndpoint())
app.add_route('/api/unsave/{id:int}', api.UnsaveEndpoint())
app.add_route('/api/follow/{username}', api.FollowEndpoint())
app.add_route('/api/unfollow/{username}', api.UnfollowEndpoint())

app.add_route('/feed', resources.FeedResource())
app.add_route('/following', resources.FollowingResource())
app.add_route('/followers', resources.FollowersResource())
app.add_route('/mentions', resources.MentionsResource())
app.add_route('/replies', resources.RepliesResource())
app.add_route('/saves', resources.SavesResource())

app.add_route('/links', resources.LinksResource())
app.add_route('/members', resources.MembersResource())
app.add_route('/space/{name}', resources.SpaceResource())
app.add_route('/spaces', resources.SpacesResource())
# app.add_route('/trending', resources.TrendingResource())
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
app.add_route('/unlock', resources.UnlockResource())
app.add_route('/unlock/{token}', resources.UnlockResource(), suffix="link")

app.add_route('/account', resources.AccountResource())
app.add_route('/account/change', resources.AccountResource(), suffix="change")
app.add_route('/account/delete', resources.AccountResource(), suffix="delete")
app.add_route('/account/export', resources.AccountResource(), suffix="export")

app.add_route('/profile', resources.ProfileResource())
app.add_route('/details', resources.DetailsResource())

app.add_route('/incomers', resources.IncomersResource())
app.add_route('/incomers/destroy', resources.IncomersResource(), suffix="destroy")

app.add_route('/reply/{id:int}', resources.ReplyResource())
app.add_route('/edit/{id:int}', resources.EditResource())
app.add_route('/{username}/approve', resources.IncomersResource(), suffix="approve")
app.add_route('/{username}', resources.MemberResource())

if DEBUG:
    app.add_route('/static/{filename}', resources.StaticResource())

application = app
