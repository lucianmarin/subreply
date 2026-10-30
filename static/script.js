function ajax(path, method, type, callback) {
    var xhr = new XMLHttpRequest();
    xhr.open(method, path, true);
    xhr.responseType = type;
    xhr.onreadystatechange = function () {
        if (this.readyState == 4) {
            callback(this.status == 200 ? this.response : null);
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
    var url = new URL(window.location.href);
    url.searchParams.set("p", page);
    element.onclick = null;
    ajax(url.pathname + url.search, "get", "text", function (data) {
        if (data == null) {
            element.innerText = "retry";
            element.className = "warn";
            element.onclick = getPage;
            return;
        }
        loader.remove();
        items.insertAdjacentHTML("beforeend", data);
    });
}

function postDelete(event, call, status) {
    // delete/unsend will always be last children in the parent html tag
    event.preventDefault();
    var element = event.currentTarget;
    var small = element.parentElement;
    var id = element.dataset.id;
    var confirm = element.nextElementSibling;
    if (!element.dataset.confirm) {
        confirm = document.createElement("a");
        element.innerText = "undo";
        element.className = "gone";
        element.dataset.confirm = "yes";
        confirm.innerText = "yes";
        confirm.className = "warn";
        confirm.onclick = remove;
        small.appendChild(confirm);
    } else {
        element.innerText = call;
        element.className = "";
        element.dataset.confirm = "";
        confirm.remove();
    }

    function remove(event) {
        event.preventDefault();
        var undo = element.onclick;
        element.onclick = null;
        confirm.onclick = null;
        ajax("/api/" + call + "/" + id, "post", "json", function (data) {
            if (data && data.status == status) {
                var state = document.createElement("b");
                state.innerText = data.status;
                small.appendChild(state);
                confirm.remove();
                element.remove();
            } else {
                element.onclick = undo;
                confirm.innerText = "retry";
                confirm.onclick = remove;
            }
        });
    }
}

function postSave(event, call) {
    event.preventDefault();
    var reverse = call == "save" ? "unsave" : "save";
    var element = event.currentTarget;
    var id = element.dataset.id;
    var rebind = function (next) {
        return function (ev) {
            ev.preventDefault();
            postSave(ev, next);
        };
    };
    element.onclick = null;
    ajax("/api/" + call + "/" + id, "post", "json", function (data) {
        if (data && data.status == reverse) {
            element.innerText = data.status;
            element.className = data.status == "unsave" ? "gone" : "";
            element.onclick = rebind(reverse);
        } else {
            element.innerText = "retry";
            element.className = "warn";
            element.onclick = rebind(call);
        }
    });
}

function postFollow(event, call) {
    event.preventDefault();
    var reverse = call == "follow" ? "unfollow" : "follow";
    var element = event.currentTarget;
    var username = element.dataset.username;
    var rebind = function (next) {
        return function (ev) {
            ev.preventDefault();
            postFollow(ev, next);
        };
    };
    element.onclick = null;
    ajax("/api/" + call + "/" + username, "post", "json", function (data) {
        if (data && data.status == reverse) {
            element.innerText = data.status;
            element.className = data.status == "unfollow" ? "action" : "accent";
            element.onclick = rebind(reverse);
        } else {
            element.innerText = "retry";
            element.className = "warn";
            element.onclick = rebind(call);
        }
    });
}

function expand(element, limit = 640) {
    if (!element) return;
    var padding = 10;
    element.style.height = "auto";
    element.style.height = element.scrollHeight - padding + "px";
    if (limit) {
        element.style.backgroundColor = element.value.length > limit ? "var(--redsmoke)" : "var(--whitesmoke)";
    }
}

function inline(event) {
    if (event.isComposing || event.keyCode == 229) return;
    if (event.key == "Enter") {
        event.preventDefault();
    }
}

function send(event) {
    // fix for Japanese/Chinese/Korean IME
    if (event.isComposing || event.keyCode == 229) return;
    if (event.key == "Enter") {
        event.preventDefault();
        var form = event.currentTarget.closest("form");
        if (form) form.requestSubmit();
    }
}

function postClear(event) {
    event.preventDefault();
    var element = event.currentTarget;
    var load = element.parentElement;
    var member = element.dataset.member;
    if (!element.dataset.confirm) {
        var sep = document.createElement("span");
        var confirm = document.createElement("a");
        sep.innerHTML = " &mdash; ";
        element.innerText = "undo";
        element.className = "gone";
        element.dataset.confirm = "yes";
        confirm.innerText = "yes";
        confirm.className = "warn";
        confirm.onclick = clear;
        load.appendChild(sep);
        load.appendChild(confirm);
    } else {
        element.innerText = "clear out";
        element.className = "";
        element.dataset.confirm = "";
        load.replaceChildren(element);
    }

    function clear(event) {
        event.preventDefault();
        var undo = element.onclick;
        element.onclick = null;
        confirm.onclick = null;
        ajax("/api/" + member + "/clear", "post", "json", function (data) {
            if (data && data.status == "cleared") {
                var state = document.createElement("b");
                state.innerText = data.status;
                load.replaceChildren(state);
            } else {
                element.onclick = undo;
                confirm.innerText = "retry";
                confirm.onclick = clear;
            }
        });
    }
}
