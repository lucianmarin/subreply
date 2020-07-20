from falcon import API
from falcon.constants import MEDIA_HTML

from app import api, resources
from project.settings import DEBUG


app = API(media_type=MEDIA_HTML)

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
app.add_route('/saved', resources.SavedResource())

app.add_route('/search', resources.SearchResource())
app.add_route('/people', resources.PeopleResource())
app.add_route('/trending', resources.TrendingResource())

app.add_route('/about', resources.AboutResource())
app.add_route('/login', resources.LoginResource())
app.add_route('/logout', resources.LogoutResource())
app.add_route('/register', resources.RegisterResource())

app.add_route('/password', resources.PasswordResource())
app.add_route('/settings', resources.SettingsResource())

app.add_route('/reset/{code}', resources.ChangeResource())
app.add_route('/reset', resources.ResetResource())

app.add_route('/edit/{base}', resources.EditResource())
app.add_route('/set/{sample}', resources.SetResource())
app.add_route('/{username}/{base}', resources.ReplyResource())
app.add_route('/{username}/unfollow', resources.ActionResource(), suffix="unf")
app.add_route('/{username}/follow', resources.ActionResource(), suffix="f")
app.add_route('/{username}/replies', resources.ProfileResource(), suffix='re')
app.add_route('/{username}', resources.ProfileResource(), suffix='th')

if DEBUG:
    app.add_route('/static/{filename}', resources.StaticResource())

application = app
