from falcon import App
from falcon.constants import MEDIA_HTML

from app import api, resources
from project.settings import DEBUG

app = App(media_type=MEDIA_HTML)

app.req_options.auto_parse_form_urlencoded = True
app.req_options.strip_url_path_trailing_slash = True

app.resp_options.secure_cookies_by_default = not DEBUG

app.add_route('/', resources.MainResource())

app.add_route('/api/unsend/{id:int}', api.UnsendEndpoint())
app.add_route('/api/delete/{id:int}', api.DeleteEndpoint())
app.add_route('/api/save/{id:int}', api.SaveEndpoint())
app.add_route('/api/unsave/{id:int}', api.UnsaveEndpoint())
app.add_route('/api/follow/{username}', api.FollowEndpoint())
app.add_route('/api/unfollow/{username}', api.UnfollowEndpoint())

app.add_route('/feed', resources.FeedResource())
# app.add_route('/following', resources.FollowingResource())
app.add_route('/followers', resources.FollowersResource())
app.add_route('/replies', resources.RepliesResource())
app.add_route('/mentions', resources.MentionsResource())
app.add_route('/messages', resources.MessagesResource())

app.add_route('/discover', resources.DiscoverResource())
app.add_route('/people', resources.PeopleResource())
app.add_route('/trending', resources.TrendingResource())

app.add_route('/news/{id:int}', resources.ArticleResource(), suffix="linker")
app.add_route('/news', resources.ArticlesResource(), suffix="news")
app.add_route('/read/{id:int}', resources.ArticleResource(), suffix="reader")
app.add_route('/read', resources.ArticlesResource(), suffix="read")

app.add_route('/sitemap', resources.SitemapResource())
app.add_route('/about', resources.AboutResource())
app.add_route('/login', resources.LoginResource())
app.add_route('/logout', resources.LogoutResource())
app.add_route('/register', resources.RegisterResource())
app.add_route('/unlock', resources.UnlockResource())
app.add_route('/unlock/{token}', resources.UnlockResource(), suffix="link")

app.add_route('/account', resources.AccountResource())
app.add_route('/account/change', resources.AccountResource(), suffix="change")
app.add_route('/account/delete', resources.AccountResource(), suffix="delete")
app.add_route('/account/export', resources.AccountResource(), suffix="export")

app.add_route('/options', resources.OptionsResource())
app.add_route('/social', resources.SocialResource())
app.add_route('/lobby', resources.LobbyResource())

app.add_route('/edit/{id:int}', resources.EditResource())
app.add_route('/reply/{id:int}', resources.ReplyResource())
app.add_route('/{username}/destroy', resources.LobbyResource(), suffix="destroy")
app.add_route('/{username}/approve', resources.LobbyResource(), suffix="approve")
app.add_route('/{username}/saved', resources.SavedResource())
app.add_route('/{username}/message', resources.MessageResource())
app.add_route('/{username}', resources.ProfileResource())

if DEBUG:
    app.add_route('/static/{filename}', resources.StaticResource())

application = app
