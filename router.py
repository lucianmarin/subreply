from falcon import App
from falcon.constants import MEDIA_HTML

from app import api, resources, xhr
from project.settings import DEBUG

app = App(media_type=MEDIA_HTML)

app.req_options.strip_url_path_trailing_slash = True

app.resp_options.secure_cookies_by_default = not DEBUG

app.add_route('/', resources.MainResource())

app.add_route('/api', resources.APIResource())
# post
app.add_route('/api/login', api.LoginEndpoint())
app.add_route('/api/register', api.RegisterEndpoint())
app.add_route('/api/post', api.PostEndpoint())
# app.add_route('/api/{username}/send', api.SendEndpoint())
# app.add_route('/api/add', api.AddEndpoint())
# patch
# app.add_route('/api/edit/{id:int}', api.EditEndpoint())
# app.add_route('/api/update/{id:int}', api.UpdateEndpoint())
# app.add_route('/api/profile', api.ProfileEndpoint())
# delete
# app.add_route('/api/delete/{id:int}', api.DeleteEndpoint())
# app.add_route('/api/erase/{id:int}', api.EraseEndpoint())
# get
app.add_route('/api/feed', api.FeedEndpoint())
app.add_route('/api/sub/{hashtag}', api.ChannelEndpoint())
app.add_route('/api/reply/{id:int}', api.ReplyEndpoint())
app.add_route('/api/following', api.FollowingEndpoint())
app.add_route('/api/followers', api.FollowersEndpoint())
app.add_route('/api/mentions', api.MentionsEndpoint())
app.add_route('/api/replies', api.RepliesEndpoint())
app.add_route('/api/saved', api.SavedEndpoint())
app.add_route('/api/people', api.PeopleEndpoint())
app.add_route('/api/discover', api.DiscoverEndpoint())
app.add_route('/api/trending', api.TrendingEndpoint())
app.add_route('/api/channels', api.ChannelsEndpoint())
app.add_route('/api/messages', api.MessagesEndpoint())
app.add_route('/api/notifications', api.NotificationsEndpoint())
app.add_route('/api/{username}', api.MemberEndpoint())
app.add_route('/api/{username}/chat', api.ChatEndpoint())

app.add_route('/xhr/erase/{id:int}', xhr.WorkCallback(), suffix="erase")
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
app.add_route('/messages', resources.MessagesResource())
app.add_route('/replies', resources.RepliesResource())
app.add_route('/saved', resources.SavedResource())

app.add_route('/sub/{hashtag}', resources.FeedResource(), suffix="sub")
app.add_route('/channels', resources.ChannelsResource())

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

app.add_route('/add', resources.AddResource())

app.add_route('/update/{id:int}', resources.UpdateResource())
app.add_route('/reply/{id:int}', resources.ReplyResource())
app.add_route('/edit/{id:int}', resources.EditResource())
app.add_route('/{username}/message', resources.MessageResource())
app.add_route('/{username}/destroy', resources.DestroyResource())
app.add_route('/{username}', resources.MemberResource())

if DEBUG:
    app.add_route('/static/{filename}', resources.StaticResource())
    app.add_route('/static/route159/{filename}', resources.StaticResource("route159"))

application = app
