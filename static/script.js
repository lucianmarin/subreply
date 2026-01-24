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

function getNextPage() {
    var items = document.getElementsByClassName('list')[0].children;
    var element = items[items.length - 1].children[0].children[0];
    if (element.innerText == "Load more") {
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

function toggle(event) {
    event.preventDefault();
    var element = event.currentTarget;
    var desc = element.parentElement.nextElementSibling;
    desc.classList.toggle("none");
}

function expand(element, limit = 640, padding = 10) {
    element.style.height = "auto";
    element.style.height = element.scrollHeight - padding + "px";
    element.style.backgroundColor =
        element.value.length > limit ? "var(--redsmoke)" : "var(--whitesmoke)";
}

function send(event) {
    if (event.keyCode == 13) {
        event.preventDefault();
        event.currentTarget.parentElement.submit();
    }
}
