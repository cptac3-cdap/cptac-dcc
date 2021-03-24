var log = false;
function generateUuid() {
    var date = new Date().getTime();
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
        var r = ((date + 16) * Math.random()).toFixed() % 16;
        if (c !== 'x') {
            /*jslint bitwise: true */
            r = r & 0x3 | 0x8;
            /*jslint bitwise: false */
        }
        return r.toString(16);
    });
}
var uuid = generateUuid();

document.addEventListener("AsperaConnectCheck", function(event) {
    safari.extension.dispatchMessage("AsperaConnectCheck");
});

// Detect extension
var attemptNumber = 1;
var timeout = 30000;
var retryTimer = setInterval(function(){
    if (timeout < 0){
        clearInterval(retryTimer);
        return;
    }
    attemptNumber += 1;
    var detector = document.getElementById("aspera-connect-detector");
    if (detector) {
        detector.setAttribute("extension-enable", "true");
        timeout = -1;
    }
    timeout -= 500;
}, 500);

var detector = document.getElementById("aspera-connect-detector");
var extensionEnable = 'false';
// find detector
if (detector) {
    extensionEnable = detector.getAttribute('extension-enable');
}
if (extensionEnable != 'true') {
    document.addEventListener("AsperaConnectRequest", function(event) {
        // Copy to a new object because Safari 10 event is read only
        var req = event.detail;
        if (req)
            req.frame_id = uuid;
        safari.extension.dispatchMessage("AsperaConnectRequest", req);
    });

    safari.self.addEventListener("message", function(event) {
        if (log)
            console.log('Content script received message: ' + JSON.stringify(event.message));
        if (event.name == "AsperaConnectResponse") {
            if (event.message && event.message.frame_id == uuid) {
                document.dispatchEvent(new CustomEvent('AsperaConnectResponse', { 'detail': event.message }));
            }
        } else if (event.name == "AsperaConnectCheckResponse") {
            document.dispatchEvent(new CustomEvent('AsperaConnectCheckResponse', { 'detail': event.message }));
        }
    });
}
