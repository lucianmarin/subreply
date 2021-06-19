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

app.add_route('/feed', resources.FeedResource())
app.add_route('/replying', resources.ReplyingResource())
app.add_route('/following', resources.FollowingResource())
app.add_route('/followers', resources.FollowersResource())
app.add_route('/mentions', resources.MentionsResource())
app.add_route('/replies', resources.RepliesResource())
app.add_route('/saves', resources.SavesResource())

app.add_route('/discover', resources.DiscoverResource())
app.add_route('/people', resources.PeopleResource())
app.add_route('/trending', resources.TrendingResource())

app.add_route('/about', resources.AboutResource())
app.add_route('/emoji', resources.EmojiResource())

app.add_route('/login', resources.LoginResource())
app.add_route('/logout', resources.LogoutResource())
app.add_route('/register', resources.RegisterResource())
app.add_route('/unlock', resources.UnlockResource())
app.add_route('/unlock/{token}', resources.UnlockResource(), suffix="lnk")

app.add_route('/account', resources.AccountResource())
app.add_route('/account/change', resources.AccountResource(), suffix="chg")
app.add_route('/account/delete', resources.AccountResource(), suffix="del")

app.add_route('/options', resources.OptionsResource())
app.add_route('/social', resources.SocialResource())

app.add_route('/edit/{base}', resources.EditResource())
app.add_route('/{username}/{base}', resources.ReplyResource())
app.add_route('/{username}/destroy', resources.ActionResource(), suffix="dst")
app.add_route('/{username}/unfollow', resources.ActionResource(), suffix="unf")
app.add_route('/{username}/follow', resources.ActionResource(), suffix="flw")
app.add_route('/{username}/replies', resources.ProfileResource(), suffix="re")
app.add_route('/{username}', resources.ProfileResource(), suffix="th")

if DEBUG:
    app.add_route('/static/{filename}', resources.StaticResource())

application = app
