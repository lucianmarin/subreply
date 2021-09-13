function ajax(path, method='post', type='json', callback) {
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

function loadPage(event, number) {
    event.preventDefault();
    var link = event.currentTarget;
    var loader = link.parentElement
    var items = loader.parentElement;
    var url = window.location.pathname + '?p=' + number;
    link.innerText = "Loading...";
    ajax(url, 'get', 'text', function (data) {
        loader.remove();
        items.innerHTML = items.innerHTML + data;
    })
}

function postDelete(event) {
    event.preventDefault();
    var element = event.currentTarget;
    var small = element.parentElement;
    var id = element.dataset.id;
    if (id != "0") {
        var confirm = document.createElement('a');
        element.innerText = "undo";
        confirm.innerText = "yes";
        confirm.onclick = function (event) {
            event.preventDefault();
            ajax('/api/delete/' + id, 'post', 'json', function (data) {
                if (data.status == 'deleted') {
                    element.innerText = data.status;
                    element.onclick = function (ev) {
                        ev.preventDefault();
                    }
                    element.style.cursor = "default";
                    confirm.remove();
                } else {
                    confirm.innerText = "error";
                    confirm.style.cursor = "default";
                }
            })
        }
        small.appendChild(confirm);
        element.dataset.id = "0";
        element.dataset.oldId = id;
    } else {
        element.innerText = "delete";
        var confirm = element.nextElementSibling;
        confirm.remove();
        element.dataset.id = element.dataset.oldId;
        element.dataset.oldId = "0";
    }
}

function postSave(event) {
    event.preventDefault();
    var element = event.currentTarget;
    var id = element.dataset.id;
    ajax('/api/save/' + id, 'post', 'json', function (data) {
        if (data.status == 'unsave') {
            element.innerText = data.status;
            element.onclick = function (ev) {
                ev.preventDefault();
                postUnsave(ev);
            }
        }
    })
}

function postUnsave(event) {
    event.preventDefault();
    var element = event.currentTarget;
    var id = element.dataset.id;
    ajax('/api/unsave/' + id, 'post', 'json', function (data) {
        if (data.status == 'save') {
            element.innerText = data.status;
            element.onclick = function (ev) {
                ev.preventDefault();
                postSave(ev);
            }
        }
    })
}

function postFollow(event) {
    event.preventDefault();
    var element = event.currentTarget;
    var username = element.dataset.username;
    ajax('/api/follow/' + username, 'post', 'json', function (data) {
        if (data.status == 'unfollow') {
            element.innerText = data.status;
            element.onclick = function (ev) {
                ev.preventDefault();
                postUnfollow(ev);
            }
        }
    })
}

function postUnfollow(event) {
    event.preventDefault();
    var element = event.currentTarget;
    var username = element.dataset.username;
    ajax('/api/unfollow/' + username, 'post', 'json', function (data) {
        if (data.status == 'follow') {
            element.innerText = data.status;
            element.onclick = function (ev) {
                ev.preventDefault();
                postSave(ev);
            }
        }
    })
}

function expand(element, padding=10, limit=480) {
    var logo = document.getElementsByClassName('logo')[0];
    var link = logo.children[0];
    if (element.value) {
        link.innerText = limit - element.value.length;
    } else {
        link.innerText = link.dataset.value;
    }
    if (element.value.length > limit) {
        link.style.color = 'var(--orange)';
    } else {
        link.style.color = 'var(--black)';
    }
    element.style.height = 'auto';
    element.style.height = (element.scrollHeight - padding) + 'px';
    element.value = element.value.normalize('NFD').replace(/[^\x00-\x7F]/g, "");
}

function send(event) {
    if (event.keyCode == 13) {
        event.preventDefault();
        event.currentTarget.parentElement.submit();
    }
}
