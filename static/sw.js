self.addEventListener("install", function () {
    self.skipWaiting();
});

self.addEventListener("activate", function (event) {
    event.waitUntil(clients.claim());
});

self.addEventListener("push", function (event) {
    var data = {};
    if (event.data) {
        try {
            data = event.data.json();
        } catch (e) {
            data = { title: "Subreply", body: event.data.text() };
        }
    }
    var title = data.title || "Subreply";
    var body = data.body || "";
    var url = data.url || "/";
    var tag = data.tag || "default";

    event.waitUntil(
        self.registration.showNotification(title, {
            body: body,
            icon: "/static/192.png",
            badge: "/static/192.png",
            tag: tag,
            data: { url: url },
        })
    );
});

self.addEventListener("notificationclick", function (event) {
    event.notification.close();
    var url = event.notification.data && event.notification.data.url;
    if (url) {
        event.waitUntil(
            clients.matchAll({ type: "window", includeUncontrolled: true }).then(function (clientList) {
                for (var i = 0; i < clientList.length; i++) {
                    var client = clientList[i];
                    if (client.url.indexOf(url) !== -1 && "focus" in client) {
                        return client.focus();
                    }
                }
                if (clients.openWindow) {
                    return clients.openWindow(url);
                }
            })
        );
    }
});
