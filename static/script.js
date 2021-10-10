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

function getPage(event, number) {
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

function postSave(event, call) {
    event.preventDefault();
    var reverse = call == 'save' ? 'unsave' : 'save';
    var element = event.currentTarget;
    var id = element.dataset.id;
    ajax('/api/' + call + '/' + id, 'post', 'json', function (data) {
        if (data.status == reverse) {
            element.innerText = data.status;
            element.onclick = function (ev) {
                ev.preventDefault();
                postSave(ev, reverse);
            }
        }
    })
}

function postFollow(event, call) {
    event.preventDefault();
    var reverse = call == 'follow' ? 'unfollow' : 'follow';
    var element = event.currentTarget;
    var username = element.dataset.username;
    ajax('/api/' + call + '/' + username, 'post', 'json', function (data) {
        if (data.status == reverse) {
            element.innerText = data.status;
            element.className = "action";
            element.onclick = function (ev) {
                ev.preventDefault();
                postFollow(ev, reverse);
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
        link.style.color = 'var(--gray)';
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
