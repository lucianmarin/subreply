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
    var loader = event.currentTarget.parentElement
    var items = loader.parentElement;
    var url = window.location.pathname + '?p=' + number;
    console.log(number);
    console.log(url);
    ajax(url, 'get', 'text', function (data) {
        loader.remove()
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

function expand(element, height=10) {
    element.style.height = 'auto';
    element.style.height = (element.scrollHeight - height) + 'px';
}

function send(event) {
    if (event.keyCode == 13) {
        event.preventDefault();
        event.currentTarget.parentElement.submit();
    }
}
