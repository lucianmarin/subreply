function ajax(path, method = "post", type = "json", callback) {
    var xhr = new XMLHttpRequest();
    xhr.open(method, path, true);
    xhr.responseType = type;
    xhr.onreadystatechange = function () {
        if (this.readyState == 4 && this.status == 200) {
            callback(xhr.response);
        }
    };
    xhr.send();
}

function getPage(event) {
    event.preventDefault();
    var element = event.currentTarget;
    var page = element.dataset.page;
    var loader = element.parentElement.parentElement;
    var items = loader.parentElement;
    var url = window.location.pathname + "?p=" + page;
    element.innerText = "Loading...";
    ajax(url, "get", "text", function (data) {
        loader.remove();
        items.innerHTML = items.innerHTML + data;
    });
}

function postDelete(event, call, status) {
    event.preventDefault();
    var element = event.currentTarget;
    var small = element.parentElement;
    var id = element.dataset.id;
    if (id != "0") {
        var confirm = document.createElement("a");
        element.innerText = "undo";
        confirm.innerText = "yes";
        confirm.onclick = function (event) {
            event.preventDefault();
            ajax("/api/" + call + "/" + id, "post", "json", function (data) {
                if (data.status == status) {
                    var state = document.createElement("b");
                    state.innerText = data.status;
                    small.appendChild(state);
                    confirm.remove();
                    element.remove();
                } else {
                    confirm.innerText = "error";
                    confirm.style.cursor = "default";
                }
            });
        };
        small.appendChild(confirm);
        element.dataset.id = "0";
        element.dataset.oldId = id;
    } else {
        element.innerText = call;
        var confirm = element.nextElementSibling;
        confirm.remove();
        element.dataset.id = element.dataset.oldId;
        element.dataset.oldId = "0";
    }
}

function postSave(event, call) {
    event.preventDefault();
    var reverse = call == "save" ? "unsave" : "save";
    var element = event.currentTarget;
    var id = element.dataset.id;
    ajax("/api/" + call + "/" + id, "post", "json", function (data) {
        if (data.status == reverse) {
            element.innerText = data.status;
            element.onclick = function (ev) {
                ev.preventDefault();
                postSave(ev, reverse);
            };
        }
    });
}

function postFollow(event, call) {
    event.preventDefault();
    var reverse = call == "follow" ? "unfollow" : "follow";
    var element = event.currentTarget;
    var username = element.dataset.username;
    ajax("/api/" + call + "/" + username, "post", "json", function (data) {
        if (data.status == reverse) {
            element.innerText = data.status;
            element.className = data.status == "unfollow" ? "action" : "accent";
            element.onclick = function (ev) {
                ev.preventDefault();
                postFollow(ev, reverse);
            };
        }
    });
}

function expand(element, limit = 640) {
    var padding = 10;
    element.style.height = "auto";
    element.style.height = element.scrollHeight - padding + "px";
    if (limit) {
        element.style.backgroundColor = element.value.length > limit ? "var(--redsmoke)" : "var(--whitesmoke)";
    }
}

function inline(event) {
    if (event.keyCode == 13) {
        event.preventDefault();
    }
}

function send(event) {
    if (event.keyCode == 13) {
        event.preventDefault();
        event.currentTarget.parentElement.submit();
    }
}

function urlBase64ToUint8Array(base64String) {
    var padding = '='.repeat((4 - base64String.length % 4) % 4);
    var base64 = (base64String + padding).replace(/\-/g, '+').replace(/_/g, '/');
    var rawData = window.atob(base64);
    var output = new Uint8Array(rawData.length);
    for (var i = 0; i < rawData.length; ++i) {
        output[i] = rawData.charCodeAt(i);
    }
    return output;
}

function updatePushUI(sub) {
    var state = document.getElementById('push-state');
    var link = document.getElementById('push-toggle');
    if (!state || !link) return;
    if (sub && sub.endpoint === window.serverEndpoint) {
        state.innerText = 'on';
        link.innerText = 'Turn off';
        link.onclick = togglePush;
    } else {
        state.innerText = 'off';
        link.innerText = 'Turn on';
        link.onclick = togglePush;
    }
}

function togglePush(event) {
    event.preventDefault();
    if (!('serviceWorker' in navigator && 'PushManager' in window)) {
        return;
    }
    navigator.serviceWorker.ready.then(function (reg) {
        reg.pushManager.getSubscription().then(function (sub) {
            if (sub && sub.endpoint === window.serverEndpoint) {
                sub.unsubscribe().then(function () {
                    fetch('/api/push/unsubscribe', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' }
                    });
                    window.serverEndpoint = '';
                    updatePushUI(null);
                });
            } else {
                (window.serverEndpoint
                    ? fetch('/api/push/unsubscribe', { method: 'POST', headers: { 'Content-Type': 'application/json' } }).then(function () { window.serverEndpoint = ''; })
                    : Promise.resolve()
                ).then(function () {
                    return sub ? sub.unsubscribe() : Promise.resolve();
                }).then(function () {
                    return fetch('/api/vapid-key').then(function (r) { return r.json(); });
                }).then(function (data) {
                    return reg.pushManager.subscribe({
                        userVisibleOnly: true,
                        applicationServerKey: urlBase64ToUint8Array(data.publicKey)
                    });
                }).then(function (sub) {
                    var ep = sub.endpoint;
                    return fetch('/api/push/subscribe', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            endpoint: ep,
                            p256dh: btoa(String.fromCharCode.apply(null, new Uint8Array(sub.getKey('p256dh')))),
                            auth: btoa(String.fromCharCode.apply(null, new Uint8Array(sub.getKey('auth'))))
                        })
                    }).then(function () {
                        window.serverEndpoint = ep;
                        updatePushUI({ endpoint: window.serverEndpoint });
                    });
                });
            }
        });
    });
}


