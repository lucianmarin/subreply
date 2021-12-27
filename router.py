from falcon import App
from falcon.constants import MEDIA_HTML

from app import api, resources
from project.settings import DEBUG

app = App(media_type=MEDIA_HTML)

app.req_options.auto_parse_form_urlencoded = True
app.req_options.strip_url_path_trailing_slash = True

app.resp_options.secure_cookies_by_default = not DEBUG

app.add_route('/', resources.MainResource())

app.add_route('/api/delete/{id}', api.DeleteEndpoint())
app.add_route('/api/save/{id}', api.SaveEndpoint())
app.add_route('/api/unsave/{id}', api.UnsaveEndpoint())
app.add_route('/api/follow/{username}', api.FollowEndpoint())
app.add_route('/api/unfollow/{username}', api.UnfollowEndpoint())

app.add_route('/feed', resources.FeedResource())
app.add_route('/following', resources.FollowingResource())
app.add_route('/followers', resources.FollowersResource())
app.add_route('/mentions', resources.MentionsResource())
app.add_route('/replies', resources.RepliesResource())
app.add_route('/saved', resources.SavedResource())

app.add_route('/discover', resources.DiscoverResource())
app.add_route('/people', resources.PeopleResource())
app.add_route('/trending', resources.TrendingResource())

app.add_route('/about', resources.AboutResource())
# app.add_route('/emoji', resources.EmojiResource())

app.add_route('/login', resources.LoginResource())
app.add_route('/logout', resources.LogoutResource())
app.add_route('/register', resources.RegisterResource())
app.add_route('/unlock', resources.UnlockResource())
app.add_route('/unlock/{token}', resources.UnlockResource(), suffix="lnk")

app.add_route('/account', resources.AccountResource())
app.add_route('/account/change', resources.AccountResource(), suffix="chg")
app.add_route('/account/delete', resources.AccountResource(), suffix="del")
app.add_route('/account/export', resources.AccountResource(), suffix="exp")

app.add_route('/options', resources.OptionsResource())
app.add_route('/social', resources.SocialResource())
app.add_route('/lobby', resources.LobbyResource())

app.add_route('/edit/{id}', resources.EditResource())
app.add_route('/reply/{id}', resources.ReplyResource())
app.add_route('/{username}/destroy', resources.LobbyResource(), suffix="dst")
app.add_route('/{username}/approve', resources.LobbyResource(), suffix="apv")
app.add_route('/{username}', resources.ProfileResource())

if DEBUG:
    app.add_route('/static/{filename}', resources.StaticResource())

application = app
