function capitalize(s) {
    return s.charAt(0).toUpperCase() + s.slice(1)
}

function ajax(path, callback) {
    var xhr = new XMLHttpRequest();
    xhr.open('post', path, true);
    xhr.responseType = 'json';
    xhr.onreadystatechange = function () {
        if (this.readyState == 4 && this.status == 200) {
            callback(xhr.response);
        }
    };
    xhr.send();
}

function get(path, callback) {
    var xhr = new XMLHttpRequest();
    xhr.open('get', path, true);
    xhr.responseType = 'text';
    xhr.onreadystatechange = function () {
        if (this.readyState == 4 && this.status == 200) {
            callback(xhr.response);
        }
    };
    xhr.send();
}

function loadMore(element, page) {
    var parent = element.parentElement;
    element.innerHTML = "Loading...";
    get('?p=' + page, function (data) {
        parent.removeChild(element);
        parent.innerHTML += data;
    })
}

function showcase(element) {
    div = document.createElement('div');
    div.className = 'showcase';
    img = document.createElement('img');
    img.src = element.src;
    img.height = '240';
    img.width = '240';
    img.onclick = function (ev) {
        document.body.removeChild(div);
        document.body.style.overflow = 'auto';
    }
    div.append(img);
    document.body.prepend(div);
    document.body.style.overflow = 'hidden';
}

function postDelete(event) {
    event.preventDefault();
    var element = event.currentTarget;
    var id = element.dataset.id;
    ajax('/api/delete/' + id, function (data) {
        if (data.status == 'deleted') {
            element.innerText = data.status;
            element.onclick = function (ev) {
                ev.preventDefault();
            }
        }
    })
}

function postSave(event) {
    event.preventDefault();
    var element = event.currentTarget;
    var id = element.dataset.id;
    ajax('/api/save/' + id, function (data) {
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
    ajax('/api/unsave/' + id, function (data) {
        if (data.status == 'save') {
            element.innerText = data.status;
            element.onclick = function (ev) {
                ev.preventDefault();
                postSave(ev);
            }
        }
    })
}

function switcher(element) {
    op = element.nextElementSibling;
    by = element.nextElementSibling.nextElementSibling;
    if (op.style.display == 'none') {
        op.style.display = 'inline';
        by.style.display = 'none';
    } else {
        op.style.display = 'none';
        by.style.display = 'inline';
    }
}

function expand(element, height=10) {
    element.style.height = 'auto';
    element.style.height = (element.scrollHeight - height) + 'px';
}

function send(event) {
    if (event.keyCode === 13 && !event.shiftKey) {
        event.preventDefault();
        event.currentTarget.parentElement.submit();
    }
}

function picture(element) {
    var label = element.previousElementSibling,
        view = label.previousElementSibling,
        file = element.files[0];
    if (file) {
        view.style.backgroundImage = 'url(' + URL.createObjectURL(file) + ')';
        label.innerHTML = element.value.replace(/.*[\/\\]/, '');
    }
}
